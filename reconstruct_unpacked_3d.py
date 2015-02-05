#!/usr/bin/env python

import os
import argh
import numpy as np
from time import time
from pact_helpers import notifyCli, loadOptions
from pact_helpers import find_delay_idx, load_hdf5_data
from pact_helpers import save_reconstructed_image
from pact_helpers import update_progress_with_time
from preprocess import subfunc_wiener, subfunc_exact

import pycuda.driver as cuda
from pycuda.compiler import SourceModule
from StringIO import StringIO

KERNEL_CU_FILE = 'reconstruct_3d_kernel.cu'
PULSE_STR = ""
PULSE_FILE = 'PULSE_ARRANGEMENTS.txt'
with open(PULSE_FILE) as fid:
    PULSE_STR = fid.read()


def rearrange_pa_data(paData):
    """rearrange paData array according to 8 firing order
    """
    nSamples, nSteps, zSteps = paData.shape
    assert nSteps == 512
    # load pulse list from the pre-defined string
    sio = StringIO(PULSE_STR)
    pulseList = np.loadtxt(sio, dtype=np.int)
    # pulse list was created based on MATLAB's 1-starting index
    # minus 1 to correct for the 0-starting index in Python
    pulseList = pulseList - 1
    numGroup = pulseList.shape[0]
    paDataE = np.zeros((nSamples, nSteps / numGroup, zSteps * numGroup),
                       dtype=np.float32, order='F')
    for zi in range(zSteps):
        for fi in range(numGroup):
            paDataE[:, :, zi * numGroup + fi] = paData[:, pulseList[fi, :], zi]
    return paDataE, pulseList, numGroup


def reconstruction_3d_stational(paData, reconOpts,
                                progress=update_progress_with_time):
    """3D reconstruction algorithm for stational scanning
    see Jun's focal-line reconstruction paper and codes for details
    """
    # reading parameters from option dict
    lenR = reconOpts['Len_R']
    R = reconOpts['R']
    vm = reconOpts['V_M']
    iniAngle = reconOpts['ini_angle']
    zPerStep = reconOpts['z_per_step']
    xSize = reconOpts['x_size']
    ySize = reconOpts['y_size']
    zSize = reconOpts['z_size']
    xCenter = reconOpts['center_x']
    yCenter = reconOpts['center_y']
    rf = reconOpts['resolution_factor']
    zrf = reconOpts['z_resolution']
    fs = reconOpts['fs']
    nSamples, nSteps, zSteps = paData.shape
    zCenter = zPerStep * zSteps / 2
    # use the first z step data to calibrate DAQ delay
    delayIdx = find_delay_idx(paData[:, :, 0], fs)
    delayIdx = delayIdx.astype(np.float32)
    anglePerStep = 2 * np.pi / nSteps
    nPixelx = int(round(xSize * rf))
    nPixely = int(round(ySize * rf))
    nPixelz = int(round(zSize * zrf))
    # note range is 0-start indices
    xRange = (np.arange(1, nPixelx + 1, 1, dtype=np.float32)
              - nPixelx / 2) * xSize / nPixelx + xCenter
    yRange = (np.arange(nPixely, 0, -1, dtype=np.float32)
              - nPixely / 2) * ySize / nPixely + yCenter
    zRange = (np.arange(1, nPixelz + 1, 1, dtype=np.float32)
              - nPixelz / 2) * zSize / nPixelz + zCenter
    # receiver position
    angleStep1 = iniAngle / 180.0 * np.pi
    detectorAngle = np.arange(0, nSteps, 1, dtype=np.float32)\
        * anglePerStep + angleStep1
    xReceive = np.cos(detectorAngle) * R
    yReceive = np.sin(detectorAngle) * R
    zReceive = np.arange(0, zSteps, dtype=np.float32) * zPerStep
    # create buffer on GPU for reconstructed image
    reImg = np.zeros((nPixely, nPixelx, nPixelz), order='C', dtype=np.float32)
    d_reImg = cuda.mem_alloc(nPixely * nPixelx * nPixelz * 4)
    cuda.memcpy_htod(d_reImg, reImg)
    # back projection loop
    notifyCli('Reconstruction starting. Keep patient.')
    d_xRange = cuda.mem_alloc(xRange.nbytes)
    cuda.memcpy_htod(d_xRange, xRange)
    d_yRange = cuda.mem_alloc(yRange.nbytes)
    cuda.memcpy_htod(d_yRange, yRange)
    d_zRange = cuda.mem_alloc(zRange.nbytes)
    cuda.memcpy_htod(d_zRange, zRange)
    # get module right before execution of function
    MOD = SourceModule(open(KERNEL_CU_FILE, 'r').read())
    bpk = MOD.get_function('backprojection_kernel')
    d_paDataLine = cuda.mem_alloc(nSamples * 4)
    # convert to single
    paData = paData.astype(np.float32)
    st_all = time()
    for zi in range(zSteps):
        for ni in range(nSteps):
            # print ni
            cuda.memcpy_htod(d_paDataLine, paData[:, ni, zi])
            bpk(d_reImg, d_paDataLine, d_xRange, d_yRange, d_zRange,
                xReceive[ni], yReceive[ni], zReceive[zi],
                np.float32(lenR), np.float32(vm), delayIdx[ni],
                np.float32(fs), np.uint32(nSamples),
                grid=(nPixelx, nPixely), block=(nPixelz, 1, 1))
        et = time()
        # use the execution time of the last loop to guess the remaining time
        time_remaining = ((zSteps - zi + 1) * (et - st_all) / (zi + 1)) / 60.0
        progress(zi + 1, zSteps, time_remaining)
    cuda.memcpy_dtoh(reImg, d_reImg)
    et_all = time()
    notifyCli(
        'Total time elapsed: {:.2f} mins'.format((et_all - st_all) / 60.0))
    return reImg


def reconstruction_3d(paData, reconOpts, ctx,
                      progress=update_progress_with_time):
    """3D reconstruction algorithm
    see Jun's focal-line reconstruction paper and codes for details
    """
    # reading parameters from option dict
    lenR = reconOpts['Len_R']
    R = reconOpts['R']
    vm = reconOpts['V_M']
    iniAngle = reconOpts['ini_angle']
    zPerStep = reconOpts['z_per_step']
    xSize = reconOpts['x_size']
    ySize = reconOpts['y_size']
    zSize = reconOpts['z_size']
    xCenter = reconOpts['center_x']
    yCenter = reconOpts['center_y']
    rf = reconOpts['resolution_factor']
    zrf = reconOpts['z_resolution']
    fs = reconOpts['fs']
    # use the first z step data to calibrate DAQ delay
    delayIdx = find_delay_idx(paData[:, :, 0], fs)
    delayIdx = delayIdx.astype(np.float32)
    # rearrange paData array according to firing order
    notifyCli('Re-arranging raw RF data according to firing squence')
    # DEBUGGING
    paData = paData.astype(np.float32)
    paData, pulseList, numGroup = rearrange_pa_data(paData)
    nSamples, nSteps, zSteps = paData.shape
    # notice the z step size is divided by firing group count
    zPerStep = zPerStep / numGroup
    zCenter = zPerStep * zSteps / 2
    # notice nSteps is now 64!!
    anglePerStep = 2 * np.pi / nSteps / numGroup
    nPixelx = int(xSize * rf)
    nPixely = int(ySize * rf)
    nPixelz = int(zSize * zrf)
    # note range is 0-start indices
    xRange = (np.arange(1, nPixelx + 1, 1, dtype=np.float32)
              - nPixelx / 2) * xSize / nPixelx + xCenter
    yRange = (np.arange(nPixely, 0, -1, dtype=np.float32)
              - nPixely / 2) * ySize / nPixely + yCenter
    zRange = (np.arange(1, nPixelz + 1, 1, dtype=np.float32)
              - nPixelz / 2) * zSize / nPixelz + zCenter
    # receiver position
    angleStep1 = iniAngle / 180.0 * np.pi
    detectorAngle = np.arange(0, nSteps * numGroup, 1, dtype=np.float32)\
        * anglePerStep + angleStep1
    xReceive = np.cos(detectorAngle) * R
    yReceive = np.sin(detectorAngle) * R
    zReceive = np.arange(0, zSteps, dtype=np.float32) * zPerStep
    # create buffer on GPU for reconstructed image
    reImg = np.zeros((nPixely, nPixelx, nPixelz),
                     order='C', dtype=np.float32)
    d_reImg = cuda.mem_alloc(nPixely * nPixelx * nPixelz * 4)
    cuda.memcpy_htod(d_reImg, reImg)
    d_cosAlpha = cuda.mem_alloc(nPixely * nPixelx * nSteps * numGroup * 4)
    d_tempc = cuda.mem_alloc(nPixely * nPixelx * nSteps * numGroup * 4)
    d_paDataLine = cuda.mem_alloc(nSamples * 4)
    # back projection loop
    notifyCli('Reconstruction starting. Keep patient.')
    d_xRange = cuda.mem_alloc(xRange.nbytes)
    cuda.memcpy_htod(d_xRange, xRange)
    d_yRange = cuda.mem_alloc(yRange.nbytes)
    cuda.memcpy_htod(d_yRange, yRange)
    d_zRange = cuda.mem_alloc(zRange.nbytes)
    cuda.memcpy_htod(d_zRange, zRange)
    d_xReceive = cuda.mem_alloc(xReceive.nbytes)
    cuda.memcpy_htod(d_xReceive, xReceive)
    d_yReceive = cuda.mem_alloc(yReceive.nbytes)
    cuda.memcpy_htod(d_yReceive, yReceive)
    # get module right before execution of function
    MOD = SourceModule(open(KERNEL_CU_FILE, 'r').read())
    precomp = MOD.get_function('calculate_cos_alpha_and_tempc')
    bpk = MOD.get_function('backprojection_kernel_fast')
    # compute cosAlpha and tempc
    st_all = time()
    precomp(d_cosAlpha, d_tempc, d_xRange, d_yRange,
            d_xReceive, d_yReceive, np.float32(lenR),
            grid=(nPixelx, nPixely), block=(nSteps * numGroup, 1, 1))
    ctx.synchronize()
    notifyCli('Done pre-computing cosAlpha and tempc.')
    st = time()
    for zi in range(zSteps):
        # find out the index of fire at each virtual plane
        fi = zi % numGroup
        for ni in range(nSteps):
            # transducer index
            ti = pulseList[fi, ni]
            cuda.memcpy_htod(d_paDataLine, paData[:, ni, zi])
            bpk(d_reImg, d_paDataLine, d_cosAlpha, d_tempc,
                d_zRange, zReceive[zi], np.float32(lenR),
                np.float32(vm), delayIdx[ti], np.float32(fs),
                np.uint32(ti), np.uint32(nSteps * numGroup),
                np.uint32(nSamples),
                grid=(nPixelx, nPixely), block=(nPixelz, 1, 1))
        et = time()
        # use the execution time of the last loop to guess the remaining time
        time_remaining = ((zSteps - zi - 1) * (et - st) / (zi + 1)) / 60.0
        progress(zi + 1, zSteps, time_remaining)
    cuda.memcpy_dtoh(reImg, d_reImg)
    et_all = time()
    notifyCli(
        'Total time elapsed: {:.2f} mins'.format((et_all - st_all) / 60.0))
    return reImg


def reconstruct_3d_stational(opts, progress=update_progress_with_time):
    '''interface function for other python scripts such as Qt applications'''
    ind = opts['load']['EXP_START']
    chn_data, chn_data_3d = load_hdf5_data(opts['extra']['dest_dir'], ind)
    if opts['display']['wi']:
        notifyCli('Performing Weiner deconvolution...')
        chn_data_3d = subfunc_wiener(chn_data_3d)
    if opts['display']['exact']:
        notifyCli('Performing filtering...')
        chn_data_3d = subfunc_exact(chn_data_3d)
    # initialize pycuda properly
    cuda.init()
    dev = cuda.Device(0)
    ctx = dev.make_context()
    reImg = reconstruction_3d_stational(chn_data_3d, opts['recon'], progress)
    ctx.pop()
    del ctx
    save_reconstructed_image(reImg, opts['extra']['dest_dir'],
                             ind, opts['recon']['out_format'], '_3d')
    return reImg


def reconstruct_3d(opts, progress=update_progress_with_time):
    '''interface function for other python scripts such as Qt applications'''
    ind = opts['load']['EXP_START']
    chn_data, chn_data_3d = load_hdf5_data(opts['extra']['dest_dir'], ind)
    if opts['display']['wi']:
        notifyCli('Performing Weiner deconvolution...')
        chn_data_3d = subfunc_wiener(chn_data_3d)
    if opts['display']['exact']:
        notifyCli('Performing filtering...')
        chn_data_3d = subfunc_exact(chn_data_3d)
    # initialize pycuda properly
    cuda.init()
    dev = cuda.Device(0)
    ctx = dev.make_context()
    reImg = reconstruction_3d(chn_data_3d, opts['recon'], ctx, progress)
    ctx.pop()
    del ctx
    save_reconstructed_image(reImg, opts['extra']['dest_dir'],
                             ind, opts['recon']['out_format'], '_3d')
    return reImg


@argh.arg('opts_path', type=str, help='path to YAML option file')
def reconstruct(opts_path):
    """reconstruct from channel data
    """
    opts = loadOptions(opts_path)
    # normalize paths according to the platform
    opts['extra']['src_dir'] =\
        os.path.expanduser(os.path.normpath(opts['extra']['src_dir']))
    opts['extra']['dest_dir'] =\
        os.path.expanduser(os.path.normpath(opts['extra']['dest_dir']))
    # load data from hdf5 files
    ind = opts['load']['EXP_START']
    if opts['load']['EXP_END'] != -1 and\
       opts['load']['EXP_END'] != ind:
        notifyCli('WARNING: multiple experiments selected. '
                  'Only the first dataset will be processed')
    chn_data, chn_data_3d = load_hdf5_data(
        opts['extra']['dest_dir'], ind)
    if opts['unpack']['Show_Image'] != 0:
        notifyCli('Currently only Show_Image = 0 is supported.')
    # initialize pyCuda environment
    cuda.init()
    dev = cuda.Device(0)
    ctx = dev.make_context()
    reImg = reconstruction_3d(chn_data_3d, opts['recon'])
    ctx.pop()
    del ctx
    save_reconstructed_image(reImg, opts['extra']['dest_dir'],
                             ind, 'tiff', '_3d')

if __name__ == '__main__':
    argh.dispatch_command(reconstruct)

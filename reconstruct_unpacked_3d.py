#!/usr/bin/env python

import os
import argh
import numpy as np
from time import time
from pact_helpers import *

import pycuda.autoinit
import pycuda.driver as cuda
from pycuda.compiler import SourceModule

from scipy.signal import hilbert

KERNEL_CU_FILE = 'reconstruct_3d_kernel.cu'
MOD = SourceModule(open(KERNEL_CU_FILE, 'r').read())

def reconstruction_3d(paData, reconOpts):
  """3D reconstruction algorithm
  see Jun's focal-line reconstruction paper and codes for details
  """
  nSamples, nSteps, zSteps = paData.shape
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
  zCenter = zPerStep*zSteps/2
  rf = reconOpts['resolution_factor']
  zrf = reconOpts['z_resolution']
  fs = reconOpts['fs']
  algorithm = reconOpts['algorithm']
  if algorithm == 'envelope':
    notifyCli('Extracting envelope of A-line signals')
    paData = np.abs(hilbert(paData, axis=0))
  paData = paData.astype(np.float32)
  anglePerStep = 2*np.pi/nSteps
  nPixelx = int(xSize * rf)
  nPixely = int(ySize * rf)
  nPixelz = int(zSize * zrf)
  # note range is 0-start indices
  xRange = (np.arange(1,nPixelx+1,1,dtype=np.float32)\
            - nPixelx/2) * xSize / nPixelx + xCenter
  yRange = (np.arange(nPixely,0,-1,dtype=np.float32)\
            - nPixely/2) * ySize / nPixely + yCenter
  zRange = (np.arange(1,nPixelz+1,1,dtype=np.float32)\
            - nPixelz/2) * zSize / nPixelz + zCenter
  # receiver position
  angleStep1 = iniAngle / 180.0 * np.pi
  detectorAngle = np.arange(0,nSteps,1,dtype=np.float32)\
                  * anglePerStep + angleStep1
  xReceive = np.cos(detectorAngle) * R
  yReceive = np.sin(detectorAngle) * R
  zReceive = np.arange(0,zSteps,dtype=np.float32) * zPerStep
  # create buffer on GPU for reconstructed image
  reImg = np.zeros((nPixely, nPixelx, nPixelz), order='C', dtype=np.float32)
  d_reImg = cuda.mem_alloc(nPixely*nPixelx*nPixelz*4)
  cuda.memcpy_htod(d_reImg, reImg)
  # use the first z step data to calibrate DAQ delay
  delayIdx = find_delay_idx(paData[:,:,0], fs)
  delayIdx = delayIdx.astype(np.float32)
  # back projection loop
  notifyCli('Reconstruction starting. Keep patient.')
  d_xRange = cuda.mem_alloc(xRange.nbytes)
  cuda.memcpy_htod(d_xRange, xRange)
  d_yRange = cuda.mem_alloc(yRange.nbytes)
  cuda.memcpy_htod(d_yRange, yRange)
  d_zRange = cuda.mem_alloc(zRange.nbytes)
  cuda.memcpy_htod(d_zRange, zRange)
  bpk = MOD.get_function('backprojection_kernel')
  d_paDataLine = cuda.mem_alloc(nSamples*4)
  st_all = time()
  for zi in range(zSteps):
    st = time()
    for ni in range(nSteps):
      cuda.memcpy_htod(d_paDataLine, paData[:,ni,zi])
      bpk(d_reImg, d_paDataLine, d_xRange, d_yRange, d_zRange,
          xReceive[ni], yReceive[ni], zReceive[zi],
          np.float32(lenR), np.float32(vm), delayIdx[ni],
          np.float32(fs), np.uint32(nSamples),
          grid=(nPixelx,nPixely), block=(nPixelz,1,1))
    et = time()
    # use the execution time of the last loop to guess the remaining time
    time_remaining = ((zSteps - zi) * (et - st)) / 60.0
    update_progress_with_time(zi+1, zSteps, time_remaining)
  cuda.memcpy_dtoh(reImg, d_reImg)
  et_all = time()
  notifyCli('Total time elapsed: {:.2f} mins'.format((et_all-st_all)/60.0))
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
    notifyCli('WARNING: multiple experiments selected. '\
              'Only the first dataset will be processed')
  chn_data, chn_data_3d = load_hdf5_data(
    opts['extra']['dest_dir'], ind)
  if opts['unpack']['Show_Image'] != 0:
    notifyCli('Currently only Show_Image = 0 is supported.')
  reImg = reconstruction_3d(chn_data_3d, opts['recon'])
  save_reconstructed_image(reImg, opts['extra']['dest_dir'], ind)

if __name__ == '__main__':
  argh.dispatch_command(reconstruct)

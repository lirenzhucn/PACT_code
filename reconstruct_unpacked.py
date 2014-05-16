#!/usr/bin/env python

import argh
import yaml
import h5py
import os
import re
import numpy as np
import scipy.signal as spsig
from pact_helpers import *
from recon_loop import recon_loop
from time import time
from matplotlib import pyplot as plt

def find_delay_idx(paData, fs):
    """find the delay value from the first few samples on
    A-lines"""
    nSteps = paData.shape[1]
    refImpulse = paData[0:100,:]
    refImpulseEnv = np.abs(spsig.hilbert(refImpulse, axis=0))
    impuMax = np.amax(refImpulseEnv, axis=0)
    # to be consistent with MATLAB's implementation ddof = 1
    tempStd = np.std(refImpulseEnv, axis=0, ddof=1)
    delayIdx = - np.ones(nSteps) * 18 / fs
    for n in range(nSteps):
        if (impuMax[n] > 3.0*tempStd[n] and impuMax[n] > 0.1):
            tmpThresh = 2*tempStd[n]
            m1 = 14
            for ii in range(14,50):
                if (refImpulse[ii-1,n] > -tmpThresh and\
                    refImpulse[ii,n] < -tmpThresh):
                    m1 = ii
                    break
            m2 = m1
            m3 = m1
            for ii in range(9,m1+1):
                if (refImpulse[ii-1,n] < tmpThresh and\
                    refImpulse[ii,n] > tmpThresh):
                    m2 = ii
                if (refImpulse[ii-1,n] > tmpThresh and\
                    refImpulse[ii,n] < tmpThresh):
                    m3 = ii
            delayIdx[n] = -float(m2 + m3 + 2) / 2 / fs
    return delayIdx

def find_index_map_and_angular_weight\
    (nSteps, xImg, yImg, xReceive, yReceive, delayIdx, vm, fs):
    totalAngularWeight = np.zeros(xImg.shape, order='F')
    idxAll = np.zeros((xImg.shape[0], xImg.shape[1], nSteps),\
                      dtype=np.uint, order='F')
    angularWeight = np.zeros((xImg.shape[0], xImg.shape[1], nSteps),\
                             order='F')
    for n in range(nSteps):
        r0 = np.sqrt(np.square(xReceive[n]) + np.square(yReceive[n]))
        dx = xImg - xReceive[n]
        dy = yImg - yReceive[n]
        rr0 = np.sqrt(np.square(dx) + np.square(dy))
        cosAlpha = np.abs((-xReceive[n]*dx-yReceive[n]*dy)/r0/rr0)
        cosAlpha = np.minimum(cosAlpha, 0.999)
        angularWeight[:,:,n] = cosAlpha/np.square(rr0)
        totalAngularWeight = totalAngularWeight + angularWeight[:,:,n]
        idx = np.around((rr0/vm - delayIdx[n]) * fs)
        idxAll[:,:,n] = idx
    return (idxAll, angularWeight, totalAngularWeight)

def reconstruction_inline(chn_data, chn_data_3d, reconOpts):
    """reconstruction function re-implemented according to
    subfunc_reconstruction2_inline.m
    """
    iniAngle = reconOpts['ini_angle']
    vm = reconOpts['V_M']
    xSize = reconOpts['x_size']
    ySize = reconOpts['y_size']
    rf = reconOpts['resolution_factor']
    xCenter = reconOpts['center_x']
    yCenter = reconOpts['center_y']
    fs = reconOpts['fs']
    R = reconOpts['R']
    # paData = np.copy(chn_data_3d[0:1300,:,:]) # cropping the first 1300
    paData = chn_data_3d
    (nSamples, nSteps, zSteps) = chn_data_3d.shape
    if nSteps != 512:
        notifyCli('ERROR: Number of transducers should be 512!')
        return None
    totalSteps = nSteps
    anglePerStep = 2 * np.pi / totalSteps
    nPixelx = xSize * rf
    nPixely = ySize * rf
    # note range is 0-start indices
    xRange = (np.arange(1,nPixelx+1,1,dtype=np.double) - nPixelx/2)\
             * xSize / nPixelx + xCenter
    yRange = (np.arange(nPixely,0,-1,dtype=np.double) - nPixely/2)\
             * ySize / nPixely + yCenter
    xImg = np.dot(np.ones((nPixely,1)), xRange.reshape((1,nPixelx)))
    yImg = np.dot(yRange.reshape((nPixely,1)), np.ones((1,nPixelx)))
    # receiver position
    angleStep1 = iniAngle / 180.0 * np.pi
    detectorAngle = np.arange(0,nSteps,1,dtype=np.double)\
                    * anglePerStep + angleStep1
    xReceive = np.cos(detectorAngle) * R
    yReceive = np.sin(detectorAngle) * R
    # reconstructed image buffer
    reImg = np.zeros((nPixely, nPixelx, zSteps), order='F')
    # use the first z step data to calibrate DAQ delay
    delayIdx = find_delay_idx(paData[:,:,0], fs)
    # find index map and angular weighting for backprojection
    notifyCli('Calculating geometry dependent backprojection'
    'parameters')
    (idxAll, angularWeight, totalAngularWeight)\
        = find_index_map_and_angular_weight\
        (nSteps, xImg, yImg, xReceive, yReceive, delayIdx, vm, fs)
    idxAll[idxAll>nSamples] = 1
    # backprojection
    notifyCli('Backprojection starts...')
    for z in range(zSteps):
        # remove DC
        paDataDC = np.dot(np.ones((nSamples-99,1)),\
                          np.mean(paData[99:nSamples,:,z],
                                  axis=0).reshape((1,paData.shape[1])))
        paData[99:nSamples,:,z] = paData[99:nSamples,:,z] - paDataDC
        temp = np.copy(paData[:,:,z], order = 'F')
        paImg = recon_loop(temp, idxAll, angularWeight,\
                           nPixelx, nPixely, nSteps)
        paImg = paImg/totalAngularWeight
        if paImg == None:
            notifyCli('WARNING: None returned as 2D reconstructed image!')
        reImg[:,:,z] = paImg
        notifyCli(str(z)+'/'+str(zSteps))
    return reImg

def load_hdf5_data(desDir, ind):
    """load hdf5 file from a specific path and an index"""
    if ind == -1:
        # find the largest index in the destination folder
        fileNameList = os.listdir(desDir)
        pattern = re.compile(r'chndata_([0-9]+).h5')
        indList = []
        for fileName in fileNameList:
            matchObj = pattern.match(fileName)
            if matchObj != None:
                indList.append(int(matchObj.group(1)))
        ind = max(indList)
    fileName = 'chndata_' + str(ind) + '.h5'
    inputPath = os.path.join(desDir, fileName)
    notifyCli('Opening data from ' + inputPath)
    f = h5py.File(inputPath, 'r')
    return (np.array(f['chndata'], order='F'),\
            np.array(f['chndata_all'], order='F'))

def save_reconstructed_image(reImg, desDir, ind):
    """save reconstructed image to a specific path and an index"""
    if ind == -1:
        # find the largest index in the destination folder
        fileNameList = os.listdir(desDir)
        pattern = re.compile(r'chndata_([0-9]+).h5')
        indList = []
        for fileName in fileNameList:
            matchObj = pattern.match(fileName)
            if matchObj != None:
                indList.append(int(matchObj.group(1)))
        ind = max(indList)
    fileName = 'reImg_' + str(ind) + '.h5'
    outPath = os.path.join(desDir, fileName)
    notifyCli('Saving image data to ' + outPath)
    f = h5py.File(outPath, 'w')
    f['reImg'] = reImg
    f.close()

@argh.arg('opts_path', type=str, help='path to YAML option file')
def reconstruct(opts_path):
    """reconstruction from channel data"""
    opts = loadOptions(opts_path)
    # load data from hdf5 files
    ind = opts['load']['EXP_START']
    if opts['load']['EXP_END'] != -1 and\
       opts['load']['EXP_END'] != ind:
        notifyCli('WARNING: multiple experiments selected. '\
                  'Only the first dataset will be processed')
    chn_data, chn_data_3d = load_hdf5_data(\
        opts['extra']['dest_dir'], ind)
    # check Show_Image and dispatch to the right method
    # currently only 0 is supported
    if opts['unpack']['Show_Image'] == 0:
        reImg = reconstruction_inline(chn_data,
                                      chn_data_3d, opts['recon'])
        save_reconstructed_image(reImg, opts['extra']['dest_dir'], ind)
        plt.imshow(reImg[:,:,0], cmap='gray')
        plt.show()
    else:
        notifyCli('Currently only Show_Image = 0 is supported.')
        reImg = reconstruction_inline(chn_data,
                                      chn_data_3d, opts['recon'])
        save_reconstructed_image(reImg, opts['extra']['dest_dir'], ind)
        plt.imshow(reImg[:,:,0], cmap='gray')
        plt.show()

if __name__ == '__main__':
    argh.dispatch_command(reconstruct)

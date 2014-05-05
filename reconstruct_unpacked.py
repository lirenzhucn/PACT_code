#!/usr/bin/env python

import argh
import yaml
import h5py
import os
import re
import numpy as np
from pact_helpers import *

def reconstruction_inline(chn_data, chn_data_3d, reconOpts):
    """reconstruction function re-implemented according to
    subfunc_reconstruction2_inline.m
    """
    paData = chn_data_3d[1:1300,:,:] # cropping the first 1300
    (nSamples, nSteps, zSteps) = chn_data_3d.shape
    if nSteps != 512:
        notifyCli('ERROR: Number of transducers should be 512!')
        return None
    totalPerSteps = nSteps
    anglePerStep = 2 * np.pi / totalPerSteps
    return (None, None)

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
    return (f['chndata'], f['chndata_all'])

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
        reconstruction_inline(chn_data,
                              chn_data_3d, opts['recon'])
    else:
        notifyCli('Currently only Show_Image = 0 is supported.')

if __name__ == '__main__':
    argh.dispatch_command(reconstruct)

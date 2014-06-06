#!/usr/bin/env python

import argh
import numpy as np
from pact_helpers import *

import pycuda.autoinit
import pycuda.gpuarray as gpuarray
import pycuda.driver as drv

import scikits.cuda.linalg as culinalg
import scikits.cuda.misc as cumisc

def find_delay_idx()

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
  anglePerStep = 2*np.pi/nSteps
  refImpulse = paData[0:100,:,:]

@argh.arg('opts_path', type=str, help='path to YAML option file')
def reconstruct(opts_path):
  """reconstruct from channel data
  """
  opts = loadOptions(opts_path)
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
  plt.imshow(reImg[:,:,reImg.shape[2]/2], cmap='gray')
  plt.show()

if __name__ == '__main__':
  argh.dispatch_command(reconstruct)

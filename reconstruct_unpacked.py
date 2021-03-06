#!/usr/bin/env python

import os
import argh
import yaml
import h5py
import numpy as np
from pact_helpers import *
from recon_loop import recon_loop, find_index_map_and_angular_weight
from time import time
from matplotlib import pyplot as plt
from scipy.signal import hilbert
from preprocess import subfunc_wiener, subfunc_exact


def reconstruction_inline(chn_data_3d, reconOpts, progress=update_progress):
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
  algorithm = reconOpts['algorithm']
  if algorithm == 'envelope':
    notifyCli('Extracting envelope of A-line signals')
    paData = np.abs(hilbert(paData, axis=0))
  (nSamples, nSteps, zSteps) = chn_data_3d.shape
  if nSteps != 512:
    notifyCli('ERROR: Number of transducers should be 512!')
    return None
  totalSteps = nSteps
  anglePerStep = 2 * np.pi / totalSteps
  nPixelx = int(round(xSize * rf))
  nPixely = int(round(ySize * rf))
  # note range is 0-start indices
  xRange = (np.arange(1, nPixelx + 1, 1, dtype=np.double)
            - nPixelx / 2) * xSize / nPixelx + xCenter
  yRange = (np.arange(nPixely, 0, -1, dtype=np.double)
            - nPixely / 2) * ySize / nPixely + yCenter
  xImg = np.dot(np.ones((nPixely, 1)), xRange.reshape((1, nPixelx)))
  yImg = np.dot(yRange.reshape((nPixely, 1)), np.ones((1, nPixelx)))
  xImg = np.copy(xImg, order='F')
  yImg = np.copy(yImg, order='F')
  # receiver position
  angleStep1 = iniAngle / 180.0 * np.pi
  detectorAngle = np.arange(0, nSteps, 1, dtype=np.double)\
      * anglePerStep + angleStep1
  xReceive = np.cos(detectorAngle) * R
  yReceive = np.sin(detectorAngle) * R
  # reconstructed image buffer
  reImg = np.zeros((nPixely, nPixelx, zSteps), order='F')
  # use the first z step data to calibrate DAQ delay
  delayIdx = find_delay_idx(paData[:,:, 0], fs)
  # find index map and angular weighting for backprojection
  notifyCli('Calculating geometry dependent backprojection'
            'parameters')
  (idxAll, angularWeight, totalAngularWeight)\
      = find_index_map_and_angular_weight\
      (nSteps, xImg, yImg, xReceive, yReceive, delayIdx, vm, fs)
  idxAll[idxAll > nSamples] = 1
  # backprojection
  notifyCli('Backprojection starts...')
  for z in range(zSteps):
    # remove DC
    paDataDC = np.dot(np.ones((nSamples - 99, 1)),
                      np.mean(paData[99:nSamples,:, z],
                              axis=0).reshape((1, paData.shape[1])))
    paData[99:nSamples,:, z] = paData[99:nSamples,:, z] - paDataDC
    temp = np.copy(paData[:,:, z], order = 'F')
    paImg = recon_loop(temp, idxAll, angularWeight,
                       nPixelx, nPixely, nSteps)
    if paImg == None:
      notifyCli('WARNING: None returned as 2D reconstructed image!')
    paImg = paImg / totalAngularWeight
    reImg[:,:, z] = paImg
    # notifyCli(str(z)+'/'+str(zSteps))
    progress(z + 1, zSteps)
  return reImg

def reconstruct_2d_average(opts, progress=update_progress):
  dest_dir = opts['extra']['dest_dir']
  ind = opts['load']['EXP_START']
  chn_data, chn_data_3d = load_hdf5_data(dest_dir, ind)
  if opts['display']['wi']:
    notifyCli('Performing Weiner deconvolution...')
    chn_data = subfunc_wiener(chn_data)
  if opts['display']['exact']:
    notifyCli('Performing filtering...')
    chn_data = subfunc_exact(chn_data)
  chn_data.resize((chn_data.shape[0], chn_data.shape[1], 1))
  reImg = reconstruction_inline(chn_data, opts['recon'], progress=progress)
  out_format = opts['recon']['out_format']
  save_reconstructed_image(reImg, dest_dir, ind, out_format)
  return reImg

def reconstruct_2d(opts, progress=update_progress):
  dest_dir = opts['extra']['dest_dir']
  ind = opts['load']['EXP_START']
  chn_data, chn_data_3d = load_hdf5_data(dest_dir, ind)
  if opts['display']['wi']:
    notifyCli('Performing Weiner deconvolution...')
    chn_data_3d = subfunc_wiener(chn_data_3d)
  if opts['display']['exact']:
    notifyCli('Performing filtering...')
    chn_data_3d = subfunc_exact(chn_data_3d)
  reImg = reconstruction_inline(chn_data_3d, opts['recon'], progress=progress)
  out_format = opts['recon']['out_format']
  save_reconstructed_image(reImg, dest_dir, ind, out_format)
  return reImg

@argh.arg('-f', '--out-format', type=str, help='Output format. hdf5 or tiff')
@argh.arg('-o', '--opts-path', type=str, help='path to YAML option file')
@argh.arg('-p', '--path-to-data-folder', type=str, help='path to the data folder')
def reconstruct(out_format='hdf5', opts_path='default_config_linux.yaml',
                path_to_data_folder=''):
  """reconstruction from channel data
  This is the command line interface of the reconstruction
  part. This function takes the path to the option file as an
  input, extracts information such as locations of the input files
  and so on, calls reconstruct_inline to do the reconstruction, and
  finally save and display the reconstructed images.
  """
  # checking out_format argument
  SUPPORTED_OUT_FORMATS = ['hdf5', 'tiff']
  if not (out_format in SUPPORTED_OUT_FORMATS):
    notifyCli('Unsupported output format: ' + out_format)
    return

  opts = loadOptions(opts_path)
  if path_to_data_folder != '':
    # put user defined path to data folder and unpack folder to opt struct.
    srcDir = os.path.normpath(path_to_data_folder)
    destDir = os.path.normpath(srcDir + '/unpack')
    opts['extra']['src_dir'] = srcDir
    opts['extra']['dest_dir'] = destDir
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
  # check Show_Image and dispatch to the right method
  # currently only 0 is supported
  if opts['unpack']['Show_Image'] != 0:
    notifyCli('Currently only Show_Image = 0 is supported.')
  reImg = reconstruction_inline(chn_data_3d, opts['recon'])
  save_reconstructed_image(reImg, opts['extra']['dest_dir'], ind, out_format)
  plt.imshow(reImg[:,:, reImg.shape[2]/2], cmap='gray')
  plt.show()

if __name__ == '__main__':
  argh.dispatch_command(reconstruct)

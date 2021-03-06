import yaml
import sys
import numpy as np
import os
import re
import h5py
import scipy.signal as spsig
import skimage.io._plugins.freeimage_plugin as fi

def notifyCli(msg):
  print msg

def update_progress(current, total):
  """update progress bar"""
  TOTAL_INDICATOR_NUM = 50
  CHAR_INDICATOR = '#'
  progress = int(float(current)/total * 100)
  numIndicator = int(float(current)/total * TOTAL_INDICATOR_NUM)
  sys.stdout.write('\r{:>3}% [{:<50}]'.format(progress,\
                                              CHAR_INDICATOR*numIndicator))
  sys.stdout.flush()
  if current == total:
    print '\tDone'

def update_progress_with_time(current, total, t):
  """update the progress bar with a time indicator instead of a
  percentage indicator
  """
  TOTAL_INDICATOR_NUM = 50
  CHAR_INDICATOR = '#'
  # progress = int(float(current)/total * 100)
  numIndicator = int(float(current)/total * TOTAL_INDICATOR_NUM)
  sys.stdout.write('\r{:>5.1f} mins [{:<50}]'.format\
                   (t, CHAR_INDICATOR*numIndicator))
  sys.stdout.flush()
  if current == total:
    print '\tDone'

def loadOptions(opts_path):
  # read and process YAML file
  f = open(opts_path)
  opts = yaml.safe_load(f)
  f.close()
  return opts

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
  chndata = np.array(f['chndata'], order='F') 
  chndata_all = np.array(f['chndata_all'], order='F')
  f.close()
  return (chndata, chndata_all)

def save_reconstructed_image(reImg, desDir, ind, out_format, sufix=''):
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
  if out_format == 'hdf5':
    fileName = 'reImg_' + str(ind) + '.h5'
    outPath = os.path.join(desDir, fileName)
    notifyCli('Saving image data to ' + outPath)
    f = h5py.File(outPath, 'w')
    f['reImg'] = reImg
    f.close()
  elif out_format == 'tiff':
    fileName = 'reImg_' + str(ind) + sufix + '.tiff'
    outPath = os.path.join(desDir, fileName)
    notifyCli('Saving image data to ' + outPath)
    imageList = [reImg[:,:,i] for i in range(reImg.shape[2])]
    fi.write_multipage(imageList, outPath)

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

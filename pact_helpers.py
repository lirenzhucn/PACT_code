import yaml
import sys
import numpy as np
import os
import re
import h5py

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
    return (np.array(f['chndata'], order='F'),\
            np.array(f['chndata_all'], order='F'))

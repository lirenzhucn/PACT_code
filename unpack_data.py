#!/usr/bin/env python
# unpack_data.py

import argh
import os
import re
import numpy as np
import h5py
import time
from unpack_speedup import daq_loop, generateChanMap
from pact_helpers import *

def renameUnindexedFile(srcDir):
    notifyCli('Renaming unindex raw data files in ' + srcDir)
    pTarget = re.compile(
        r'Board[0-9]+Experiment[0-9]+TotalFiring[0-9]+_Pack.bin')
    pExisting = re.compile(
        r'Board([0-9]+)Experiment([0-9]+)TotalFiring([0-9]+)'
        r'_Pack_([0-9]+).bin')
    # find unindex bin files and the max index
    targetFileList = []
    indexList = []
    for fileName in os.listdir(srcDir):
        if pTarget.match(fileName) != None:
            targetFileList.append(fileName)
        else:
            matchExisting = pExisting.match(fileName)
            if matchExisting != None:
                indexList.append(int(matchExisting.group(4)))

    if not targetFileList:
        notifyCli('No unindexed file found!')
        return -1
    # target index is max index + 1
    renameIndex = max(indexList) + 1
    for fileName in targetFileList:
        srcFilePath = os.path.join(srcDir, fileName)
        destFilePath = srcFilePath[:-4] + '_' +\
                       str(renameIndex) + '.bin'
        notifyCli(srcFilePath)
        notifyCli('\t->' + destFilePath)
        os.rename(srcFilePath, destFilePath)

    return renameIndex

def readBinFile(filePath, dtype, packSize, totFirings, numExpr):
    f = open(filePath)
    if f == None:
        notifyCli('File not found: ' + filePath)
        return None
    tempData = np.fromfile(f, dtype=dtype)
    f.close()
    return tempData.reshape((6*totFirings*numExpr,
                             packSize)).transpose()

def saveChnData(chnData, chnDataAll, destDir, ind):
    fileName = 'chndata_' + str(ind) + '.h5'
    outputPath = os.path.join(destDir, fileName)
    notifyCli('Saving data to ' + outputPath)
    f = h5py.File(outputPath, 'w')
    f['chndata'] = chnData
    f['chndata_all'] = chnDataAll
    f.close()

def read_channel_data(opts):
    srcDir = opts['extra']['src_dir']
    destDir = opts['extra']['dest_dir']
    startInd = opts['load']['EXP_START']
    endInd = opts['load']['EXP_END']
    packSize = opts['unpack']['PackSize']
    totFirings = opts['unpack']['TotFirings']
    numBoards = opts['unpack']['NumBoards']

    if startInd == -1 or endInd == -1:
        nextInd = renameUnindexedFile(srcDir)
        if nextInd == -1:
            return
        startInd = nextInd
        endInd = nextInd

    fileNameList = os.listdir(srcDir)

    # chn_data_list = [None] * (endInd - startInd + 1)
    chn_data_all_list = [None] * (endInd - startInd + 1)

    for ind in range(startInd, endInd+1):
        packData = [] # list of pack data
        # search through file list to find "experiment" (z step)
        # number for this particular index
        pattern = re.compile(r'Board([0-9]+)' +
                             r'Experiment([0-9]+)TotalFiring' +
                             str(totFirings) + '_Pack_' +
                             str(ind) + '.bin')
        numExpr = -1
        for fileName in fileNameList:
            matchObj = pattern.match(fileName)
            if matchObj != None:
                _numExpr = int(matchObj.group(2))
                if _numExpr != numExpr and numExpr != -1:
                    notifyCli('Warning: multiple' +
                              '\"experiment\" numbers found!' +
                              ' Last found will be used.')
                numExpr = _numExpr
        if numExpr == -1:
            notifyCli('Warning: no file found. Skipping index '
                      + str(ind))
            continue # no file to process, skip this index
        for boardId in range(numBoards):
            boardName = opts['unpack']['BoardName'][boardId]
            fileName = boardName + 'Experiment' + str(numExpr) +\
                'TotalFiring' + str(totFirings) + '_Pack_' +\
                str(ind) + '.bin'
            filePath = os.path.join(srcDir, fileName)
            tempData = readBinFile(filePath,
                                   opts['extra']['dtype'],
                                   packSize, totFirings, numExpr)
            tempData = tempData[0:2600,:]
            packData.append(tempData)

        # interpret raw data into channel format
        # see daq_loop.c for original implementation
        chanMap = generateChanMap(opts['unpack']['NumElements'])
        notifyCli('Starting daq_loop...')
        startTime = time.time()
        chnData, chnDataAll = daq_loop(packData[0], packData[1],
                                       chanMap, numExpr)
        endTime = time.time()
        notifyCli('daq_loop ended. ' + str(endTime - startTime) +\
                      ' s elapsed.')
        # fix bad channels
        chnData = -chnData/numExpr
        badChannels =\
            [(chnInd-1) for chnInd in opts['unpack']['BadChannels']]
        chnData[:,badChannels] = -chnData[:,badChannels]
        chnDataAll = np.reshape(chnDataAll,
                                (opts['unpack']['DataBlockSize'],
                                 opts['unpack']['NumElements'],
                                 numExpr), order='F')
        chnDataAll[:,badChannels,:] = -chnDataAll[:,badChannels,:]
        
        if opts['extra']['save_raw']:
            # check if the directory is there or not
            if not os.path.exists(opts['extra']['dest_dir']):
                os.mkdir(opts['extra']['dest_dir'])
            # saving channel RF data to HDF5 file
            saveChnData(chnData, chnDataAll,
                        opts['extra']['dest_dir'], ind)

        # chn_data_list[endInd-startInd] = chnData
        chn_data_all_list[ind-startInd] = chnDataAll

    # arrange raw data into a big 3D matrix
    size_of_axis = lambda x, ind: (x.shape[ind] if x != None else 0)
    z_steps = [size_of_axis(x, 2) for x in chn_data_all_list]
    time_seq_len_list = [size_of_axis(x, 0) for x in chn_data_all_list]
    detector_num_list = [size_of_axis(x, 1) for x in chn_data_all_list]
    num_z_step = sum(z_steps)
    time_seq_len = max(time_seq_len_list)
    detector_num = max(detector_num_list)
    chn_data_3d = np.zeros((time_seq_len, detector_num, num_z_step),
                           order='F', dtype=np.double)
    zInd = 0
    for chn_data_all in chn_data_all_list:
        if chn_data_all != None:
            zSize = chn_data_all.shape[2]
            chn_data_3d[:,:,zInd:zInd+zSize] = chn_data_all
            zInd += zSize
    # averaging over z steps
    chn_data = np.mean(chn_data_3d, axis=2)
    return chn_data, chn_data_3d

def pre_process(chn_data, chn_data_3d, opts):
    if (opts['display']['wi'] or
        opts['display']['pc'] or
        opts['display']['exact'] or
        opts['display']['denoise']):
        notifyCli('Warning: Pre-processing flag(s) found, '
                  'but none is currently supported.')
    return chn_data, chn_data_3d

def unpack(opts):
    chn_data, chn_data_3d =\
        read_channel_data(opts)
    chn_data, chn_data_3d =\
        pre_process(chn_data, chn_data_3d, opts)

@argh.arg('-o', '--opt-file', type=str, help='YAML file of options')
@argh.arg('-p', '--path-to-data-folder', type=str,
          help='path to the data folder')
@argh.arg('-ns', '--no-save', help='flag to override saving raw data option')
def main(opt_file='default_config_linux.yaml',
         path_to_data_folder='', no_save=False):
    # read and process YAML file
    opts = loadOptions(opt_file)
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
    # processing overriding flags
    if no_save:
        notifyCli('Overriding the save_raw flag to False')
        opts['extra']['save_raw'] = False

    unpack(opts)

if __name__ == '__main__':
    argh.dispatch_command(main)

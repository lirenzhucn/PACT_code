# unpack_data.py

import argparse
import yaml
import os
import re
import numpy as np
import h5py
import time
from unpack_speedup import daq_loop, generateChanMap

def notifyCli(msg):
    print msg

def renameUnindexedFile(srcDir):
    notifyCli('Renaming unindex raw data files in ' + srcDir)
    pTarget = re.compile(r'Board[0-9]+Experiment[0-9]+TotalFiring[0-9]+_Pack.bin')
    pExisting = re.compile(r'Board([0-9]+)Experiment([0-9]+)TotalFiring([0-9]+)_Pack_([0-9]+).bin')
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
        destFilePath = srcFilePath[:-4] + '_'+str(renameIndex) + '.bin'
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
    return tempData.reshape((6*totFirings*numExpr, packSize)).transpose()

# def generateChanMap(NumElements):
#     temp = np.zeros(128, dtype=np.uint32)
#     chanOffset = [1*128, 3*128, 2*128, 0*128]
#     temp[0:8] = [1, 2, 3, 4, 68, 67, 66, 65]
#     for n in range(1,16):
#         temp[n*8:(n+1)*8] = temp[(n-1)*8:n*8] + 4
#     chanMap = np.zeros(NumElements, dtype=np.uint32)
#     for n in range(1,5):
#         chanMap[(n-1)*128:n*128] = temp + chanOffset[n-1]
#     return chanMap

def saveChnData(chnData, chnDataAll, destDir, ind):
    fileName = 'chndata_' + str(ind) + '.h5'
    outputPath = os.path.join(destDir, fileName)
    f = h5py.File(outputPath, 'w')
    f['chndata'] = chnData
    f['chndata_all'] = chnDataAll
    f.close()

def unpack(opts):
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
        notifyCli('daq_loop ended. ' + str(endTime - startTime) + ' s elapsed.')
        chnData = -chnData/numExpr
        # saving channel RF data to HDF5 file
        saveChnData(chnData, chnDataAll, opts['extra']['dest_dir'], ind)

def main():
    parser = argparse.ArgumentParser(
        description='unpack PACT raw data to single HDF5 files')
    parser.add_argument('opt_file', metavar='opt_file', type=str,
                        help='YAML file of options')
    # parse arguments
    args = parser.parse_args()
    # read and process YAML file
    f = open(args.opt_file)
    opts = yaml.safe_load(f)
    f.close()

    unpack(opts)

if __name__ == '__main__':
    main()

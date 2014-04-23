from __future__ import division
import numpy as np
cimport numpy as np

cimport cython

DTYPE = np.double
ctypedef np.double_t DTYPE_t

@cython.boundscheck(False)
def generateChanMap(int NumElements):
    cdef np.ndarray[unsigned int, ndim=1] temp =\
        np.zeros(128, dtype=np.uint32)
    chanOffset = [1*128, 3*128, 2*128, 0*128]
    temp[0:8] = [1, 2, 3, 4, 68, 67, 66, 65]
    for n in range(1,16):
        temp[n*8:(n+1)*8] = temp[(n-1)*8:n*8] + 4
    cdef np.ndarray[unsigned int, ndim=1] chanMap =\
        np.zeros(NumElements, dtype=np.uint32)
    for n in range(1,5):
        chanMap[(n-1)*128:n*128] = temp + chanOffset[n-1]
    return chanMap

@cython.boundscheck(False)
def daq_loop(np.ndarray[unsigned int, ndim=2] packData1,
             np.ndarray[unsigned int, ndim=2] packData2,
             np.ndarray[unsigned int, ndim=1] ChanMap,
             int NumExperiments):
    cdef int hex3ff = 1023
    cdef Py_ssize_t DataBlockSize = 1300
    cdef Py_ssize_t NumElements = 512
    cdef Py_ssize_t TotFirings = 8
    cdef Py_ssize_t NumDaqChnsBoard = 32

    cdef np.ndarray[DTYPE_t, ndim=3] raw_data =\
        np.zeros([TotFirings,NumDaqChnsBoard,DataBlockSize],
                 dtype=DTYPE)

    cdef Py_ssize_t B, N, F, counter, i, j, channel, chan_offset
    cdef Py_ssize_t chanindex, firingindex
    cdef np.ndarray[unsigned int, ndim=2] pack_data

    cdef np.ndarray[DTYPE_t, ndim=2] chndata =\
        np.zeros([DataBlockSize, NumElements],
                 dtype=DTYPE, order='F')
    cdef np.ndarray[DTYPE_t, ndim=2] chndata_all =\
        np.zeros([DataBlockSize, NumExperiments*NumElements],
                 dtype=DTYPE, order='F')

    cdef DTYPE_t mean_data

    cdef unsigned int pd0, pd1

    for B in range(2):
        counter = 0
        chan_offset = B * TotFirings * NumDaqChnsBoard
        if B == 0:
            pack_data = packData1
        else:
            pack_data = packData2
        # print str(pack_data[0,0]) + ' ' + str(pack_data[0,1])
        for N in range(NumExperiments):
            for F in range(TotFirings):
                i = 0
                channel = 0
                while(i<6):
                    for j in range(DataBlockSize):
                        pd0 = pack_data[j*2, counter]
                        pd1 = pack_data[j*2+1, counter]
                        raw_data[F,channel,j] =\
                            <DTYPE_t>(pd0 & hex3ff)
                        raw_data[F,channel+1,j] =\
                            <DTYPE_t>(pd1 & hex3ff)
                        raw_data[F,channel+2,j] =\
                            <DTYPE_t>((pd0>>10) & hex3ff)
                        raw_data[F,channel+3,j] =\
                            <DTYPE_t>((pd1>>10) & hex3ff)
                        if (i!=2 and i!=5):
                            raw_data[F,channel+4,j] =\
                                <DTYPE_t>((pd0>>20) & hex3ff)
                            raw_data[F,channel+5,j] =\
                                <DTYPE_t>((pd1>>20) & hex3ff)
                    if (i!=2 and i!=5):
                        channel += 6
                    else:
                        channel += 4
                    i += 1
                    counter += 1
            for chanindex in range(NumDaqChnsBoard):
                for firingindex in range(TotFirings):
                    mean_data = 0
                    for i in range(DataBlockSize):
                        mean_data += raw_data[firingindex, chanindex, i]
                    mean_data /= DataBlockSize
                    for i in range(DataBlockSize):
                        raw_data[firingindex, chanindex, i] =\
                            (raw_data[firingindex, chanindex, i] - \
                                 mean_data)/NumElements
                    channel = ChanMap[chanindex*8+firingindex+chan_offset]-1
                    for i in range(DataBlockSize):
                        chndata[i, channel] +=\
                            raw_data[firingindex, chanindex, i]
                        chndata_all[i, (N*NumElements+channel)] =\
                            -raw_data[firingindex, chanindex, i]

    return chndata, chndata_all

@cython.boundscheck(False)
def recon_loop():
    pass

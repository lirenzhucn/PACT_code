#!/usr/bin/env python

import argh
import numpy as np
from time import time
from pact_helpers import *

import pycuda.autoinit
# import pycuda.gpuarray as gpuarray
import pycuda.driver as cuda
from pycuda.compiler import SourceModule

import scikits.cuda.linalg as culinalg
import scikits.cuda.misc as cumisc

MOD = SourceModule("""
#include <math.h>

#define SIGN(x) ((x) > 0.0 ? 1 : -1)

__global__ void init_image_kernel(float *img) {
  size_t xi = blockIdx.x;
  size_t yi = blockIdx.y;
  size_t zi = threadIdx.x;
  size_t imgIdx = zi + yi*blockDim.x + xi*blockDim.x*gridDim.y;
  img[imgIdx] = 0.0;
}

__global__ void backprojection_kernel
(float *img, float *paDataLine,
 float *xRange, float *yRange, float *zRange,
 float xReceive, float yReceive, float zReceive,
 float lenR, float vm, float delayIdx, float fs,
 unsigned int lineLength) {
  size_t xi = blockIdx.x;
  size_t yi = blockIdx.y;
  size_t zi = threadIdx.x;
  size_t imgIdx = zi + yi*blockDim.x + xi*blockDim.x*gridDim.y;
  float dx = xRange[xi] - xReceive;
  float dy = yRange[yi] - yReceive;
  float dz = zRange[zi] - zReceive;
  float r0 = sqrt(xReceive*xReceive + yReceive*yReceive);
  float rr0 = sqrt(dx*dx + dy*dy);
  float cosAlpha = fabs((-xReceive*dx-yReceive*dy)/r0/rr0);
  float tempc = rr0 - lenR/cosAlpha;
  rr0 = sqrt(tempc*tempc + dz*dz)*SIGN(tempc) + lenR/cosAlpha;
  if (fabs(dz/tempc) < fabs(10.0/lenR/cosAlpha)) {
    float angleWeightB = tempc/sqrt(tempc*tempc+dz*dz)*cosAlpha/(rr0*rr0);
    size_t idx0 = lround((rr0/vm-delayIdx)*fs);
    if (idx0 < lineLength) {
      img[imgIdx] += paDataLine[idx0] / angleWeightB;
    }
  }
}
""")

def reconstruction_3d(paData, reconOpts):
  """3D reconstruction algorithm
  see Jun's focal-line reconstruction paper and codes for details
  """
  paData = paData.astype(np.float32)
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
  nPixelx = xSize * rf
  nPixely = ySize * rf
  nPixelz = zSize * zrf
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
  d_xRange = cuda.mem_alloc(xRange.nbytes)
  cuda.memcpy_htod(d_xRange, xRange)
  d_yRange = cuda.mem_alloc(yRange.nbytes)
  cuda.memcpy_htod(d_yRange, yRange)
  d_zRange = cuda.mem_alloc(zRange.nbytes)
  cuda.memcpy_htod(d_zRange, zRange)
  bpk = MOD.get_function('backprojection_kernel')
  d_paDataLine = cuda.mem_alloc(nSamples*4)
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
    print (et - st)/60.0
  cuda.memcpy_dtoh(reImg, d_reImg)
  return reImg

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

if __name__ == '__main__':
  argh.dispatch_command(reconstruct)

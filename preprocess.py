"""
preprocess module that preprocesses raw RF data for specific purposes,
such as Wiener deconvolution and filtered backprojection.
"""

import numpy as np
from scipy import fftpack
from scipy.signal import lfilter
import matplotlib.pyplot as plt

def smooth(y, span):
  width = span-1+(span%2)
  c = lfilter(np.ones(width)/width, 1, y)
  cbegin = np.cumsum(y[0:width-2])
  cbegin = cbegin[0::2] / np.arange(1,width-1,2)
  cend = np.cumsum(y[:-width+1:-1])
  cend = cend[::-2] / np.arange(width-2,0,-2)
  c = np.concatenate((cbegin, c[width-1:], cend))
  return c

class RingIndexCalculator:
  def __init__(self, size):
    self.size = size
  def distFromTo(self, from_, to_):
    dist = from_ - to_
    if dist < 0: dist += self.size
    return dist
  def isAdjacent(self, idx1, idx2):
    idx1, idx2 = sorted((idx1, idx2))
    if idx2-idx1 == 1: return True
    elif idx2 == self.size-1 and idx1 == 0: return True
    else: return False
  def previousOf(self, idx):
    if idx <= 0: return self.size - 1
    else: return idx - 1
  def nextOf(self, idx):
    if idx >= self.size - 1: return 0
    else: return idx + 1
  def previousAndNext(self, idxList):
    if not idxList: return (0, 0)
    idxList = sorted(idxList)
    previous = self.previousOf(idxList[0])
    next_ = self.nextOf(idxList[-1])
    return (previous, next_)
  def groupAdjacent(self, idxList):
    idxList.sort()
    groupList = []
    currentGroup = []
    for idx in idxList:
      if not currentGroup:
        currentGroup.append(idx)
      else:
        if (self.isAdjacent(currentGroup[0], idx) or
            self.isAdjacent(currentGroup[-1], idx)):
          currentGroup.append(idx)
          currentGroup.sort()
        else:
          groupList.append(currentGroup)
          currentGroup = [idx]
    groupList.append(currentGroup)
    return groupList

def weiner_deconv(impulse_data, padata):
  nSamples, nSteps, zSteps = padata.shape
  # Wiener deconvolution
  impulse_fft = fftpack.fft(impulse_data, axis=0)
  normalize_factors = np.amax(np.absolute(impulse_fft), axis=0)
  impulse_fft = impulse_fft / normalize_factors
  impulse_ps = np.square(np.abs(impulse_fft))
  spectrum = fftpack.fft(padata, axis=0)
  powerSpectrum = np.square(np.abs(spectrum))
  max_power = np.amax(powerSpectrum, axis=0)
  cutoff = 0.01 * max_power
  impulse_fft.resize((nSamples, nSteps, 1))
  impulse_ps.resize((nSamples, nSteps, 1))
  Gf1 = np.conj(impulse_fft)*powerSpectrum
  Gf2 = impulse_ps*powerSpectrum+cutoff
  Gf = Gf1/Gf2
  results = np.real(fftpack.ifft(Gf*spectrum, axis=0))
  padata[100:,:,:] = results[100:,:,:]
  return padata

def subfunc_wiener(padata):
  nSamples, nSteps, zSteps = padata.shape
  impulse_data = np.zeros(padata.shape[0:2])
  impulse_data[0:100,:] = np.mean(padata[0:100,:,:], axis=2)
  # find low gain channels as bad channels
  ref_max = np.amax(impulse_data[0:100,:], axis=0)
  channel_cutoff = 0.2 * smooth(ref_max, 20)
  badChannelList = np.nonzero(ref_max < channel_cutoff)[0]
  # replace bad channel impulse data with those from adjacent channels
  ric = RingIndexCalculator(nSteps)
  # 1. group adjacent bad channels
  groupList = ric.groupAdjacent(list(badChannelList))
  # 2. find previous and next good channels for each group
  for idxList in groupList:
    (previous, next_) = ric.previousAndNext(idxList)
  # 3. interpolate channel signals based on distance
    for idx in idxList:
      dist_p = ric.distFromTo(idx, previous)
      dist_n = ric.distFromTo(next_, idx)
      dist_t = dist_p + dist_n
      rp = float(dist_p)/float(dist_t)
      rn = float(dist_n)/float(dist_t)
      impulse_data[0:100, idx] = impulse_data[0:100, previous] * rp +\
          impulse_data[0:100, next_] * rn
  return weiner_deconv(impulse_data, padata)

#@profile
def subfunc_exact(padata):
  nSamples, nSteps, zSteps = padata.shape
  freq = np.concatenate((range(0,nSamples/2),
                         range(-nSamples/2,0)))/\
      float(nSamples)*2*np.pi
  spectrum = fftpack.fft(padata, axis=0)
  tSeq = np.arange(0, nSamples)
  freq = freq * 1j
  freq.resize((nSamples, 1, 1))
  tSeq.resize((nSamples, 1, 1))
  diff = tSeq * np.real(fftpack.ifft(spectrum * freq, axis=0))
  return padata - diff

if __name__ == '__main__':
  import h5py
  f = h5py.File(r'C:\Users\liren\Desktop\chndata_1.h5')
  padata = np.array(f['/chndata_all'], order='F')
  f.close()
  padata = subfunc_wiener(padata)
  padata = subfunc_exact(padata)
  fo = h5py.File(r'C:\Users\liren\Desktop\test.h5', 'w')
  fo['/r2'] = padata
  fo.close()


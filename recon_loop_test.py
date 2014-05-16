import numpy as np
import recon_loop

nPixelx = 400
nPixely = 500
nSteps = 512
pa_data = np.zeros((1300, 512), order='F')
idxAll = np.zeros((nPixelx, nPixely, nSteps), order='F', dtype=np.uint)
angularWeight = np.zeros((nPixelx, nPixely, nSteps), order='F')

result = recon_loop.recon_loop(pa_data, idxAll, angularWeight,\
                               nPixelx, nPixely, nSteps)

print result.shape

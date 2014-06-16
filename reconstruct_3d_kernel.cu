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

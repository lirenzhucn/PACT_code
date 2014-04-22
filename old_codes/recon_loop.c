#include "mex.h"

void mexFunction( int nlhs, mxArray *plhs[],
                  int nrhs, const mxArray *prhs[])
{
    double *pa_data, *idxall, *angle_weightall, *pa_img;
    int Npixel_y, Npixel_x, Nstep;
    int iStep, y, x, icount, pcount, iskip;

    pa_data = mxGetPr(prhs[0]);
    idxall = mxGetPr(prhs[1]);
    angle_weightall = mxGetPr(prhs[2]);
    Npixel_y = mxGetScalar(prhs[3]);
    Npixel_x = mxGetScalar(prhs[4]);
    Nstep = mxGetScalar(prhs[5]);

    plhs[0] = mxCreateDoubleMatrix(Npixel_y, Npixel_x, mxREAL);
    pa_img = mxGetPr(plhs[0]);

    icount=0;
    for (iStep=0; iStep<Nstep; iStep++) {
        pcount=0;
        iskip=1301*iStep-1;
        for (y=0; y<Npixel_y; y++) {
            for (x=0; x<Npixel_x; x++) {
                pa_img[pcount++]+=pa_data[(int)idxall[icount]+iskip]*angle_weightall[icount];
                icount++;
            }
        }
    }

}

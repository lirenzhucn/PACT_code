#include "mex.h"

void mexFunction( int nlhs, mxArray *plhs[],
                  int nrhs, const mxArray *prhs[])
{
    double *pack_data, *ChanMap;
    int NumExperiments;
    double *chndata, *chndata_all;

    int channel, counter, chan_offset;
    int B, N, F, i, j, chanindex, firingindex;
    double mean_data;

    const int hex3ff = 1023;
    const int DataBlockSize = 1300;
    const int NumElements = 512;
    const int TotFirings = 8;
    const int NumDaqChnsBoard = 32;

    double raw_data[8][32][1300];

    ChanMap = mxGetPr(prhs[2]);
    NumExperiments = mxGetScalar(prhs[3]);

    plhs[0] = mxCreateDoubleMatrix(DataBlockSize, NumElements, mxREAL);
    plhs[1] = mxCreateDoubleMatrix(DataBlockSize, NumExperiments*NumElements, mxREAL);
    chndata = mxGetPr(plhs[0]);
    chndata_all = mxGetPr(plhs[1]);

    for (B=0; B<2; B++) {
        pack_data=mxGetPr(prhs[B]);
        chan_offset=B*TotFirings*NumDaqChnsBoard;
        counter=0;

        for (N=0; N<NumExperiments; N++) {
            for (F=0; F<TotFirings; F++) {
                for (i=0, channel=0; i<6; i++, counter++) {
                    for (j=0; j<DataBlockSize; j++) {
                        raw_data[F][channel][j]=((int)pack_data[counter*2*DataBlockSize+j*2] & hex3ff);
                        raw_data[F][channel+1][j]=((int)pack_data[counter*2*DataBlockSize+j*2+1] & hex3ff);
                        raw_data[F][channel+2][j]=(((int)pack_data[counter*2*DataBlockSize+j*2] >> 10) & hex3ff);
                        raw_data[F][channel+3][j]=(((int)pack_data[counter*2*DataBlockSize+j*2+1] >> 10) & hex3ff);
                        if (i!=2 && i!=5) {
                            raw_data[F][channel+4][j]=(((int)pack_data[counter*2*DataBlockSize+j*2] >> 20) & hex3ff);
                            raw_data[F][channel+5][j]=(((int)pack_data[counter*2*DataBlockSize+j*2+1] >> 20) & hex3ff);
                        }
                    }
                    if (i!=2 && i!=5)
                        channel+=6;
                    else
                        channel+=4;
                }
            }

            for (chanindex=0; chanindex<NumDaqChnsBoard; chanindex++) {
                for (firingindex=0; firingindex<TotFirings; firingindex++) {
                    mean_data=0;
                    for (i=0; i<DataBlockSize; i++)
                        mean_data+=(raw_data[firingindex][chanindex][i]);
                    mean_data/=DataBlockSize;
                    for (i=0; i<DataBlockSize; i++)
                        raw_data[firingindex][chanindex][i]=(raw_data[firingindex][chanindex][i]-mean_data)/NumElements;

                    channel=(int)ChanMap[chanindex*8+firingindex+chan_offset]-1;
                    for (i=0; i<DataBlockSize; i++) {
                        chndata[channel*DataBlockSize+i]+=raw_data[firingindex][chanindex][i];
                        chndata_all[(N*NumElements+channel)*DataBlockSize+i]=-raw_data[firingindex][chanindex][i];
                    }
                }
            }
        }
    }
}

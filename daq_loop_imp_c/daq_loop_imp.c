#include "daq_loop_imp.h"
#include "stdint.h"

void daq_loop_imp(const uint32_t * packDataBoard[2],
		  const double * ChanMap, const int NumExperiments,
		  double * chndata, double * chndata_all,
		  const int TotFirings, const int NumDaqChnsBoard,
		  const int DataBlockSize, const int NumElements) {
  uint32_t * pack_data;

  int channel, counter, chan_offset;
  int B, N, F, i, j, chanindex, firingindex;
  double mean_data;

  const int hex3ff = 1023;

  double raw_data[8][32][1300];

  for (B = 0; B < 2; B++) {
    pack_data = packDataBoard[B];
    chan_offset = B*TotFirings*NumDaqChnsBoard;
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

void daq_loop(const uint32_t * packDataBoard1,
	      const int sizePackDataBoard1,
	      const uint32_t * packDataBoard2,
	      const int sizePackDataBoard2,
	      const double * ChanMap,
	      const int sizeChanMap,
	      double *chndata, const int sizeChndata,
	      double *chndata_all, const int sizeChndata_all,
	      const int NumExperiments,
	      const int TotFirings, const int NumDaqChnsBoard,
	      const int DataBlockSize, const int NumElements) {
  const uint32_t *packDataBoard[2];
  packDataBoard[0] = packDataBoard1;
  packDataBoard[1] = packDataBoard2;
  daq_loop_imp(packDataBoard, ChanMap, NumExperiments, chndata, chndata_all,
	       TotFirings, NumDaqChnsBoard, DataBlockSize, NumElements);
}

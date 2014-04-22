#ifndef _DAQ_LOOP_IMP_H_
#define _DAQ_LOOP_IMP_H_

typedef unsigned int uint32_t;

void daq_loop(const uint32_t * packDataBoard1,
	      const int sizePackDataBoard1,
	      const uint32_t * packDataBoard2,
	      const int sizePackDataBoard2,
	      const double * ChanMap,
	      const int sizeChanMap,
	      double *chndata, const int sizeChndata,
	      double *chndata_all, const int sizeChndata_all,
	      const int NumExperiments,
	      const int TotFirings, const int NumDaqChansBoard,
	      const int DataBlockSize, const int NumElements);

/* void daq_loop_imp(const uint32_t * packDataBoard[2], */
/* 		  const double * ChanMap, const int NumExperiments, */
/* 		  double * chndata, double * chndata_all, */
/* 		  const int TotFirings, const int NumDaqChnsBoard, */
/* 		  const int DataBlockSize, const int NumElements); */

#endif //_DAQ_LOOP_IMP_H_

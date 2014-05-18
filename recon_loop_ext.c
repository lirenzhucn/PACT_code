#include <Python.h>
#include <numpy/arrayobject.h>
#include <math.h>
#include <stdio.h>

typedef unsigned long uint64_t;

// implementation function
void recon_loop_imp(const double *pa_data,
		    const uint64_t *idxAll,
		    const double *angularWeight,
		    int nPixelx, int nPixely, int nSteps,
		    int nTimeSamples,
		    double *pa_img) {
  int iStep, y, x, icount, pcount, iskip;

  icount = 0;
  for (iStep=0; iStep<nSteps; iStep++) {
    pcount = 0;
    iskip = nTimeSamples * iStep - 1;
    /* iskip = 1301 * iStep - 1; */
    for (y=0; y<nPixely; y++) {
      for (x=0; x<nPixelx; x++) {
	pa_img[pcount++] +=
	  pa_data[(int)idxAll[icount]+iskip] *
	  angularWeight[icount];
	icount++;
      }
    }
  }
}

// interface function
// inputs:
//   pa_data: numpy.ndarray, ndim=2, dtype=numpy.double
//   idxAll: numpy.ndarray, ndim=3, dtype=numpy.uint
//   angularWeight: numpy.ndarray, ndim=3, dtype=numpy.double
//   nPixelx: int
//   nPixely: int
//   nSteps: int
// output:
//   pa_img: numpy.ndarray, ndim=2, dtype=numpy.double
static PyObject* recon_loop(PyObject* self, PyObject* args) {
  PyArrayObject *p_pa_data, *p_idxAll, *p_angularWeight;
  int nPixelx, nPixely, nSteps;
  PyObject *p_pa_img;
  npy_intp *dim_pa_img[2];

  int paDataValid, idxAllValid, angularWeightValid;
  double *pa_data, *angularWeight;
  uint64_t *idxAll;
  double *pa_img;

  // extract argument tuple
  if (!PyArg_ParseTuple(args, "O!O!O!iii",
  			&PyArray_Type, &p_pa_data,
  			&PyArray_Type, &p_idxAll,
  			&PyArray_Type, &p_angularWeight,
  			&nPixelx, &nPixely, &nSteps)) {
    return Py_None;
  }

  // extract and validate variables
  paDataValid = (PyArray_ISFLOAT(p_pa_data)) &&
    (PyArray_CHKFLAGS(p_pa_data, NPY_ARRAY_FARRAY));
  idxAllValid = (PyArray_ISUNSIGNED(p_idxAll)) &&
    (PyArray_CHKFLAGS(p_idxAll, NPY_ARRAY_FARRAY));
  angularWeightValid = (PyArray_ISFLOAT(p_angularWeight)) &&
    (PyArray_CHKFLAGS(p_angularWeight, NPY_ARRAY_FARRAY));
  if (!paDataValid || !idxAllValid || !angularWeightValid) {
    printf("%d, %d, %d\n", paDataValid, idxAllValid, angularWeightValid);
    goto fail;
  }
  dim_pa_img[0] = nPixelx;
  dim_pa_img[1] = nPixely;
  p_pa_img = PyArray_ZEROS(2, dim_pa_img, NPY_DOUBLE, 1);
  pa_data = (double *)PyArray_DATA(p_pa_data);
  idxAll = (uint64_t *)PyArray_DATA(p_idxAll);
  angularWeight = (double *)PyArray_DATA(p_angularWeight);
  pa_img = (double *)PyArray_DATA(p_pa_img);

  // call implementation function
  recon_loop_imp(pa_data, idxAll, angularWeight,
		 nPixelx, nPixely, nSteps,
		 PyArray_SHAPE(p_pa_data)[0],
		 pa_img);

  // return value
  return p_pa_img;
  // failed situation
 fail:
  return Py_None;
}

// speed-up implementation of find_index_map_and_angular_weight
// We will not have separate implementation function this time, since
// we would like to use some numpy functions on the data, and in order
// to do so, all the arrays have to stay as PyArray_Type.
static PyObject* find_index_map_and_angular_weight(PyObject* self, PyObject* args) {
}


static PyMethodDef ReconMethods[] = {
  {"recon_loop", recon_loop, METH_VARARGS, "Reconstruction loop"},
  {"find_index_map_and_angular_weight", find_index_map_and_angular_weight,
   METH_VARARGS, "Find index map and angular weights for back-projection"},
  {NULL, NULL, 0, NULL} // the end
};

// module initialization
PyMODINIT_FUNC
initrecon_loop(void) {
  (void) Py_InitModule("recon_loop", ReconMethods);
  // IMPORTANT: this must be called
  import_array();
}

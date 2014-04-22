%module daq_loop
%{
  #define SWIG_FILE_WITH_INIT
  #include "daq_loop_imp.h"
%}

%include "numpy.i"
%init %{
  import_array();
%}

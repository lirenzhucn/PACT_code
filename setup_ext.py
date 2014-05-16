#!/usr/bin/env python
"""Combined setup script for all the extensions"""

from distutils.core import setup, Extension
from Cython.Build import cythonize
import numpy

# define the extension module
RECON_LOOP_MODULE = Extension('recon_loop',
                              sources=['recon_loop_ext.c'],
                              include_dirs=[numpy.get_include()])

UNPACK_SPEEDUP_MODULE = Extension('unpack_speedup', ['unpack_speedup.pyx'],
                                  include_dirs=[numpy.get_include()])

# run the setup
setup(ext_modules=[RECON_LOOP_MODULE])
setup(ext_modules=cythonize(UNPACK_SPEEDUP_MODULE))

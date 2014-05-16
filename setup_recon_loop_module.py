"""Set up script for compiling the recon_loop package"""

from distutils.core import setup, Extension
import numpy

# define the extension module
RECON_LOOP_MODULE = Extension('recon_loop',
                              sources=['recon_loop_ext.c'],
                              include_dirs=[numpy.get_include()])

# run the setup
setup(ext_modules=[RECON_LOOP_MODULE])

from distutils.core import setup
from distutils.extension import Extension
from Cython.Build import cythonize
import numpy

module = Extension('unpack_speedup', ['unpack_speedup.pyx'],
                   include_dirs=[numpy.get_include()])

setup(
    name = 'unpack_speedup',
    ext_modules = cythonize(module),
)

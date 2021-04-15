#!/usr/bin/env python

from setuptools import setup
from Cython.Build import cythonize

setup(ext_modules=cythonize("search_solution.pyx", language_level=3))

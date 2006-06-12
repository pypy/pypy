#! /usr/bin/env python
"""
Usage:  compilemodule.py <module-name>

Compiles the PyPy extension module from  pypy/module/<module-name>/
into a regular CPython extension module.
"""

import autopath, sys
from pypy.rpython.rctypes.tool.compilemodule import main

main(sys.argv)

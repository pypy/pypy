#! /usr/bin/env python
"""
Usage:  compilemodule.py <module-name>

Compiles the PyPy extension module from  pypy/module/<module-name>/
into a regular CPython extension module.
"""

import sys
import pypy.rpython.rctypes.implementation
from pypy.translator.goal.ann_override import PyPyAnnotatorPolicy
from pypy.rpython.rctypes.tool.cpyobjspace import CPyObjSpace
from pypy.translator.driver import TranslationDriver


def compilemodule(modname):
    "Compile a PyPy module for CPython."

    space = CPyObjSpace()
    ModuleClass = __import__('pypy.module.%s' % modname,
                             None, None, ['Module']).Module
    module = ModuleClass(space, space.wrap(modname))
    w_moduledict = module.getdict()

    XXX in-progress, for now see translator/goal/targetdemomodule.py


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print >> sys.stderr, __doc__
        sys.exit(2)
    compilemodule(sys.argv[1])

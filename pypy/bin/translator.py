#!/usr/bin/env python 

"""PyPy Translator Frontend

Glue script putting together the various pieces of the translator.
Can be used for interactive testing of the translator.

Example:

    t = Translator(func)
    t.view()                           # control flow graph

    print t.source()                   # original source
    print t.c()                        # C translation
    print t.cl()                       # common lisp translation
    print t.llvm()                     # LLVM translation

    t.simplify()                       # flow graph simplification
    a = t.annotate([int])              # pass the list of args types
    a.simplify()                       # simplification by annotator
    t.view()                           # graph + annotations under the mouse

    t.call(arg)                        # call original function
    t.dis()                            # bytecode disassemble

    a.specialize()                     # use low level operations (for C only)
    f = t.ccompile()                   # C compilation
    f = t.llvmcompile()                # LLVM compilation
    assert f(arg) == t.call(arg)       # sanity check

Some functions are provided for the benefit of interactive testing.
Try dir(test) for list of current snippets.
"""

import autopath, os, sys
from pypy.translator.translator import Translator


if __name__ == '__main__':
    from pypy.translator.test import snippet as test
    if (os.getcwd() not in sys.path and
        os.path.curdir not in sys.path):
        sys.path.insert(0, os.getcwd())
    print __doc__

    # 2.3 specific -- sanxiyn
    import os
    os.putenv("PYTHONINSPECT", "1")

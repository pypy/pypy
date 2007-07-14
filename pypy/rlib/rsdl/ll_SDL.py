#!/usr/bin/env python

from _SDL import * # suck in constants..

def _build():
    import sys
    import ctypes
    from pypy.rpython.tool import genrffi
    import _SDL

    builder = genrffi.RffiBuilder(
        includes=['SDL.h'], libraries=['SDL'], 
        include_dirs=['/usr/local/include/SDL'])
    ns = _SDL.__dict__
    builder.proc_namespace(ns)
    
    gbls = globals()
    gbls.update(builder.ns)

_build()
del _build



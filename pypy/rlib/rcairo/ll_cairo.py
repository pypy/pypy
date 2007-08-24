#!/usr/bin/env python

def _build():
    import sys
    import ctypes
    from pypy.rpython.tool import genrffi
    import _cairo

    builder = genrffi.RffiBuilder(
        includes=['cairo.h'], libraries=['cairo'], 
        include_dirs=['/usr/local/include/cairo', '/usr/include/cairo'])
    ns = _cairo.__dict__
    builder.proc_namespace(ns)
    
    gbls = globals()
    gbls.update(builder.ns)

_build()
del _build



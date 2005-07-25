#!/usr/bin/python

import autopath
import os

from pypy.rpython.module import ll_os, ll_os_path, ll_time, ll_math #XXX keep this list up-to-date
from pypy.translator.llvm2.extfunction import extfunctions

def main():
    suggested_primitives = []
    for module in (ll_os, ll_os_path, ll_time, ll_math):    #XXX keep this list up-to-date too
        suggested_primitives += [func for func in dir(module) if getattr(module.__dict__[func], 'suggested_primitive', False)]

    implemented_primitives = [f[1:] for f in extfunctions.keys()]

    missing_primitives = [func for func in suggested_primitives if func not in implemented_primitives]

    print 'rpython suggested primitives:'
    print suggested_primitives
    print
    print 'llvm implemented primitives:'
    print implemented_primitives
    print
    print 'llvm missing primitives:'
    print missing_primitives

if __name__ == '__main__':
    main()

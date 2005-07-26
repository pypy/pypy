#!/usr/bin/python

import autopath
from sets import Set

from pypy.rpython.module import ll_os, ll_os_path, ll_time, ll_math #XXX keep this list up-to-date
from pypy.translator.llvm2.module.extfunction import extfunctions

def main():
    for module in (ll_os, ll_os_path, ll_time, ll_math):    #XXX keep this list up-to-date too
        suggested_primitives   = Set( [func for func in dir(module) if getattr(module.__dict__[func], 'suggested_primitive', False)] )
        implemented_primitives = Set( [f[1:] for f in extfunctions.keys()] )
        missing_primitives     = suggested_primitives - implemented_primitives
        print 'Missing llvm primitives for %s:' % module.__name__
        for m in missing_primitives:
            print '   %s' % m

if __name__ == '__main__':
    main()

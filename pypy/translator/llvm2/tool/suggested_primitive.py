#!/usr/bin/python

import autopath
from sets import Set

from pypy.rpython.module import ll_os   #XXX keep up to date
from pypy.translator.llvm2.module.extfunction import extfunctions

def main():
    seen = Set()
    for module in (ll_os,):    #XXX keep this list up-to-date too
        suggested_primitives   = Set( [func for func in dir(module) if func not in seen and getattr(module.__dict__[func], 'suggested_primitive', False)] )
        seen |= suggested_primitives
        implemented_primitives = Set( [f[1:] for f in extfunctions.keys()] )
        missing_primitives     = suggested_primitives - implemented_primitives
        print 'Missing llvm primitives for %s:' % module.__name__
        for m in missing_primitives:
            print '   %s' % m

if __name__ == '__main__':
    main()

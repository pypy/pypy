#! /usr/bin/env python

import os, sys
from time import time
from pypy.rlib.rbigint import rbigint

# __________  Entry point  __________

def entry_point(argv):
    """
        A cutout with some benchmarks.
        Pypy default:
        18.270045
        2.512140
        14.148920
        18.576713
        6.647562

        Pypy with improvements:
        15.211410
        1.707288
        13.955348
        14.474590
        6.446812

    """
    
    t = time()
    i = rbigint.fromint(2**31)
    i2 = rbigint.fromint(2**31)
    for n in xrange(75000):
        i = i.mul(i2)

    print time() - t
    
    t = time()
    
    for n in xrange(10000):
        rbigint.pow(rbigint.fromint(n), rbigint.fromint(10**4))
        

    print time() - t
    
    t = time()
    
    for n in xrange(100000):
        rbigint.pow(rbigint.fromint(1024), rbigint.fromint(1024))
        

    print time() - t
    
    
    t = time()
    v = rbigint.fromint(2)
    for n in xrange(50000):
        v = v.mul(rbigint.fromint(2**62))
        

    print time() - t
    
    t = time()
    v2 = rbigint.fromint(2**8)
    for n in xrange(28):
        v2 = v2.mul(v2)
        

    print time() - t
    
    t = time()
    v3 = rbigint.fromint(2**62)
    for n in xrange(500000):
        v3 = v3.add(v3)
        

    print time() - t
    
    return 0

# _____ Define and setup target ___

def target(*args):
    return entry_point, None

if __name__ == '__main__':
    import sys
    res = entry_point(sys.argv)
    sys.exit(res)

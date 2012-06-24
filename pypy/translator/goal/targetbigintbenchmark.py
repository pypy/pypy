#! /usr/bin/env python

import os, sys
from time import time
from pypy.rlib.rbigint import rbigint

# __________  Entry point  __________

def entry_point(argv):
    """
        A cutout with some benchmarks.
        Pypy default:
        8.637287
        12.211942
        18.270045
        2.512140
        14.148920
        18.576713
        6.647562

        Pypy with improvements:
        9.474363
        5.797121
        10.068798
        14.770187
        1.620009
        12.054951
        14.292367
        6.440351

    """
    
    t = time()
    num = rbigint.fromint(10000000)
    for n in xrange(10000):
        rbigint.pow(rbigint.fromint(2), num)
        

    print time() - t

    t = time()
    num = rbigint.pow(rbigint.fromint(10000), rbigint.fromint(2 ** 8))
    for n in xrange(60000):
        rbigint.pow(rbigint.fromint(10**4), num, rbigint.fromint(100))
        

    print time() - t
    
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

#! /usr/bin/env python

import os, sys
from time import time
from pypy.rlib.rbigint import rbigint

# __________  Entry point  __________

def entry_point(argv):
    """
        All benchmarks are run using --opt=2 and minimark gc (default).
        
        A cutout with some benchmarks.
        Pypy default:
        2.803071
        2.366586
        2.428205
        4.408400
        4.424533
        537.338
        268.3339
        8.548186
        12.197392
        17.629869
        2.360716
        14.315827
        17.963899
        6.604541
        Sum: 901.7231250000001
        
        Pypy with improvements:
        mod by 2:  0.006297
        mod by 10000:  3.693501
        mod by 1024 (power of two):  0.011243
        Div huge number by 2**128: 2.163590
        rshift: 2.219846
        lshift: 2.689848
        Floordiv by 2: 1.460396
        Floordiv by 3 (not power of two): 4.071267
        2**10000000: 9.720923
        (2**N)**100000000 (power of two): 1.639600
        10000 ** BIGNUM % 100 1.738285
        i = i * i: 4.861456
        n**10000 (not power of two): 6.206040
        Power of two ** power of two: 0.038726
        v = v * power of two 3.633579
        v = v * v 8.180117
        v = v + v 5.006874
        Sum:  57.341588

        A pure python form of those tests where also run
        Improved pypy           | Pypy                  | CPython 2.7.3
        0.000210046768188        2.82172012329             1.38699007034
        0.123202085495           0.126130104065            8.17586708069
        0.123197078705           0.124358177185            8.34655714035
        0.0616521835327          0.0626962184906           4.88309693336
        0.0617570877075          0.0626759529114           4.88519001007
        0.000902891159058        479.282402992             (forever, I yet it run for 5min before quiting)
        1.65824794769            (forever)                 (another forever)
        0.000197887420654        6.59566307068             8.29050803185
        5.32597303391            12.1487128735             7.1309800148
        6.45182704926            15.0498359203             11.733394146
        0.000119924545288        2.13657021523             1.67227101326
        3.96346402168            14.7546520233             9.05311799049
        8.30484199524            17.0125601292             11.1488289833
        4.99971699715            6.59027791023             3.63601899147
    """
    sumTime = 0.0
    
    
    """t = time()
    by = rbigint.pow(rbigint.fromint(63), rbigint.fromint(100))
    for n in xrange(9900):
        by2 = by.lshift(63)
        rbigint.mul(by, by2)
        by = by2
        

    _time = time() - t
    sumTime += _time
    print "Toom-cook effectivity 100-10000 digits:", _time"""
    
    V2 = rbigint.fromint(2)
    num = rbigint.pow(rbigint.fromint(100000000), rbigint.fromint(1024))
    t = time()
    for n in xrange(600000):
        rbigint.mod(num, V2)
        
    _time = time() - t
    sumTime += _time
    print "mod by 2: ", _time
    
    by = rbigint.fromint(10000)
    t = time()
    for n in xrange(300000):
        rbigint.mod(num, by)
        
    _time = time() - t
    sumTime += _time
    print "mod by 10000: ", _time
    
    V1024 = rbigint.fromint(1024)
    t = time()
    for n in xrange(300000):
        rbigint.mod(num, V1024)
        
    _time = time() - t
    sumTime += _time
    print "mod by 1024 (power of two): ", _time
    
    t = time()
    num = rbigint.pow(rbigint.fromint(100000000), rbigint.fromint(1024))
    by = rbigint.pow(rbigint.fromint(2), rbigint.fromint(128))
    for n in xrange(80000):
        rbigint.divmod(num, by)
        

    _time = time() - t
    sumTime += _time
    print "Div huge number by 2**128:", _time
    
    t = time()
    num = rbigint.fromint(1000000000)
    for n in xrange(160000000):
        rbigint.rshift(num, 16)
        

    _time = time() - t
    sumTime += _time
    print "rshift:", _time
    
    t = time()
    num = rbigint.fromint(1000000000)
    for n in xrange(160000000):
        rbigint.lshift(num, 4)
        

    _time = time() - t
    sumTime += _time
    print "lshift:", _time
    
    t = time()
    num = rbigint.fromint(100000000)
    for n in xrange(80000000):
        rbigint.floordiv(num, V2)
        

    _time = time() - t
    sumTime += _time
    print "Floordiv by 2:", _time
    
    t = time()
    num = rbigint.fromint(100000000)
    V3 = rbigint.fromint(3)
    for n in xrange(80000000):
        rbigint.floordiv(num, V3)
        

    _time = time() - t
    sumTime += _time
    print "Floordiv by 3 (not power of two):",_time
    
    t = time()
    num = rbigint.fromint(10000000)
    for n in xrange(10000):
        rbigint.pow(V2, num)
        

    _time = time() - t
    sumTime += _time
    print "2**10000000:",_time

    t = time()
    num = rbigint.fromint(100000000)
    for n in xrange(31):
        rbigint.pow(rbigint.pow(V2, rbigint.fromint(n)), num)
        

    _time = time() - t
    sumTime += _time
    print "(2**N)**100000000 (power of two):",_time
    
    t = time()
    num = rbigint.pow(rbigint.fromint(10000), rbigint.fromint(2 ** 8))
    P10_4 = rbigint.fromint(10**4)
    V100 = rbigint.fromint(100)
    for n in xrange(60000):
        rbigint.pow(P10_4, num, V100)
        

    _time = time() - t
    sumTime += _time
    print "10000 ** BIGNUM % 100", _time
    
    t = time()
    i = rbigint.fromint(2**31)
    i2 = rbigint.fromint(2**31)
    for n in xrange(75000):
        i = i.mul(i2)

    _time = time() - t
    sumTime += _time
    print "i = i * i:", _time
    
    t = time()
    
    for n in xrange(10000):
        rbigint.pow(rbigint.fromint(n), P10_4)
        

    _time = time() - t
    sumTime += _time
    print "n**10000 (not power of two):",_time
    
    t = time()
    for n in xrange(100000):
        rbigint.pow(V1024, V1024)
        

    _time = time() - t
    sumTime += _time
    print "Power of two ** power of two:", _time
    
    
    t = time()
    v = rbigint.fromint(2)
    P62 = rbigint.fromint(2**62)
    for n in xrange(50000):
        v = v.mul(P62)
        

    _time = time() - t
    sumTime += _time
    print "v = v * power of two", _time
    
    t = time()
    v2 = rbigint.fromint(2**8)
    for n in xrange(28):
        v2 = v2.mul(v2)
        

    _time = time() - t
    sumTime += _time
    print "v = v * v", _time
    
    t = time()
    v3 = rbigint.fromint(2**62)
    for n in xrange(500000):
        v3 = v3.add(v3)
        

    _time = time() - t
    sumTime += _time
    print "v = v + v", _time
    
    print "Sum: ", sumTime
    
    return 0

# _____ Define and setup target ___

def target(*args):
    return entry_point, None

if __name__ == '__main__':
    import sys
    res = entry_point(sys.argv)
    sys.exit(res)

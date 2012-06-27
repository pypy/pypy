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
        2.777119
        2.316023
        2.418211
        5.147583
        5.139127
        484.5688
        334.611903
        8.637287
        12.211942
        18.270045
        2.512140
        14.148920
        18.576713
        6.647562

        Pypy with improvements:
        2.822389 # Little slower, divmod
        2.522946 # Little shower, rshift
        4.600970 # Much slower, lshift
        2.126048 # Twice as fast
        4.276203 # Little faster
        9.662745 # 50 times faster
        1.621029 # 200 times faster
        3.956685 # Twice as fast
        5.752223 # Twice as fast
        7.660295 # More than twice as fast
        0.039137 # 50 times faster
        4.437456 # 3 times faster
        9.078680 # Twice as fast
        4.995520 # 1/3 faster, add


        A pure python form of those tests where also run
        Improved pypy           | Pypy                  | CPython 2.7.3
        0.0440728664398         2.82172012329             1.38699007034
        0.1241710186            0.126130104065            8.17586708069
        0.12434387207           0.124358177185            8.34655714035
        0.0627701282501         0.0626962184906           4.88309693336
        0.0636250972748         0.0626759529114           4.88519001007
        1.20847392082           479.282402992             (forever, I yet it run for 5min before quiting)
        1.66941714287           (forever)                 (another forever)
        0.0701060295105         6.59566307068             8.29050803185
        6.55810189247           12.1487128735             7.1309800148
        7.59417295456           15.0498359203             11.733394146
        0.00144410133362        2.13657021523             1.67227101326
        5.06110692024           14.7546520233             9.05311799049
        9.19830608368           17.0125601292             11.1488289833
        5.40441417694           6.59027791023             3.63601899147
    """

    t = time()
    num = rbigint.pow(rbigint.fromint(100000000), rbigint.fromint(1024))
    by = rbigint.pow(rbigint.fromint(2), rbigint.fromint(128))
    for n in xrange(80000):
        rbigint.divmod(num, by)
        

    print time() - t
    
    t = time()
    num = rbigint.fromint(1000000000)
    for n in xrange(160000000):
        rbigint.rshift(num, 16)
        

    print time() - t
    
    t = time()
    num = rbigint.fromint(1000000000)
    for n in xrange(160000000):
        rbigint.lshift(num, 4)
        

    print time() - t
    
    t = time()
    num = rbigint.fromint(100000000)
    for n in xrange(80000000):
        rbigint.floordiv(num, rbigint.fromint(2))
        

    print time() - t
    
    t = time()
    num = rbigint.fromint(100000000)
    for n in xrange(80000000):
        rbigint.floordiv(num, rbigint.fromint(3))
        

    print time() - t
    
    t = time()
    num = rbigint.fromint(10000000)
    for n in xrange(10000):
        rbigint.pow(rbigint.fromint(2), num)
        

    print time() - t

    t = time()
    num = rbigint.fromint(100000000)
    for n in xrange(31):
        rbigint.pow(rbigint.pow(rbigint.fromint(2), rbigint.fromint(n)), num)
        

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

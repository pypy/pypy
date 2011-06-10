
""" Usage:

./targetnumpystandalone-c <bytecode> array_size

Will execute a give numpy bytecode. Arrays will be ranges (in float) modulo 10,
constants would be consecutive starting from one.

Bytecode should contain letters 'a' 'l' and 'f' so far and be correct
"""

import time
from pypy.module.micronumpy.compile import numpy_compile
from pypy.jit.codewriter.policy import JitPolicy
from pypy.rpython.annlowlevel import hlstr

def entry_point(argv):
    if len(argv) != 3:
        print __doc__
        return 1
    try:
        size = int(argv[2])
    except ValueError:
        print "INVALID LITERAL FOR INT:", argv[2]
        print __doc__
        return 3
    t0 = time.time()
    main(argv[0], size)
    print "bytecode:", bytecode, "size:", size
    print "took:", time.time() - t0
    return 0

def main(bc, size):
    if not isinstance(bc, str):
        bc = hlstr(bc) # for tests
    a = numpy_compile(bc, size)
    a = a.compute()

def target(*args):
    return entry_point, None

def jitpolicy(driver):
    return JitPolicy()

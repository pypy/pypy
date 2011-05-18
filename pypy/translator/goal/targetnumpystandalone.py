
""" Usage:

./targetnumpystandalone-c <bytecode> array_size

Will execute a give numpy bytecode. Arrays will be ranges (in float) modulo 10,
constants would be consecutive starting from one.

Bytecode should contain letters 'a' 'l' and 'f' so far and be correct
"""

import time
from pypy.module.micronumpy.numarray import SingleDimArray, Code, compute
from pypy.jit.codewriter.policy import JitPolicy

def create_array(size):
    a = SingleDimArray(size)
    for i in range(size):
        a.storage[i] = float(i % 10)
    return a

def entry_point(argv):
    if len(argv) != 3:
        print __doc__
        return 1
    bytecode = argv[1]
    for b in bytecode:
        if b not in 'alf':
            print "WRONG BYTECODE"
            print __doc__
            return 2
    try:
        size = int(argv[2])
    except ValueError:
        print "INVALID LITERAL FOR INT:", argv[2]
        print __doc__
        return 3
    no_arrays = bytecode.count('l')
    no_floats = bytecode.count('f')
    arrays = []
    floats = []
    for i in range(no_arrays):
        arrays.append(create_array(size))
    for i in range(no_floats):
        floats.append(float(i + 1))
    code = Code(bytecode, arrays, floats)
    t0 = time.time()
    compute(code)
    print "bytecode:", bytecode, "size:", size
    print "took:", time.time() - t0
    return 0

def target(*args):
    return entry_point, None

def jitpolicy(driver):
    return JitPolicy()

from pypy.translator.cli.test.runtest import check
from pypy.rpython.rarithmetic import ovfcheck

import sys

def op_add(x, y):
    try:
        return ovfcheck(x+y)
    except OverflowError:
        return 42

def op_sub(x, y):
    try:
        return ovfcheck(x-y)
    except OverflowError:
        return 42

def op_mul(x, y):
    try:
        return ovfcheck(x*y)
    except OverflowError:
        return 42

def test_overflow():
    yield check, op_add, [int, int], (sys.maxint, 1)
    yield check, op_sub, [int, int], (-sys.maxint, 1)
    yield check, op_mul, [int, int], (sys.maxint/2 + 1, 2)

# check does not exist because it involves an extensive overhaul on runtest.  See CLI's runtest for an example.
#from pypy.translator.jvm.test.runtest import check 
import py
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.rlib.rarithmetic import ovfcheck

import sys

class TestJvmOperation(JvmTest):
    def test_recursive(self):
        py.test.skip("JVM runtest lacks support to run these tests")

#def op_add(x, y):
#    try:
#        return ovfcheck(x+y)
#    except OverflowError:
#        return 42
#
#def op_sub(x, y):
#    try:
#        return ovfcheck(x-y)
#    except OverflowError:
#        return 42
#
#def op_mul(x, y):
#    try:
#        return ovfcheck(x*y)
#    except OverflowError:
#        return 42
#
#def op_lshift(x, y):
#    try:
#        return ovfcheck(x<<y)
#    except OverflowError:
#        return 42
#
#def op_neg(x):
#    try:
#        return ovfcheck(-x)
#    except OverflowError:
#        return 42
#
#def test_overflow():
#    yield check, op_add, [int, int], (sys.maxint, 1)
#    yield check, op_sub, [int, int], (-sys.maxint, 1)
#    yield check, op_mul, [int, int], (sys.maxint/2 + 1, 2)
#    yield check, op_lshift, [int, int], (2, 30)
#    yield check, op_neg, [int], (-sys.maxint-1,)


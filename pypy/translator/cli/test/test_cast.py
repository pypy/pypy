import sys

from pypy.translator.cli.test.runtest import check
from pypy.rpython.rarithmetic import r_uint, r_ulonglong, r_longlong, intmask

def to_int(x):
    return int(x)

def to_uint(x):
    return r_uint(x)

def to_float(x):
    return float(x)

def to_longlong(x):
    return r_longlong(x)


def test_bool_to_int():
    check(to_int, [bool], (True,))
    check(to_int, [bool], (False,))    

def test_bool_to_uint():
    check(to_uint, [bool], (True,))
    check(to_uint, [bool], (False,))

def test_bool_to_float():
    check(to_float, [bool], (True,))
    check(to_float, [bool], (False,))

def test_int_to_uint():
    check(to_uint, [int], (42,))

def test_int_to_float():
    check(to_float, [int], (42,))

def test_int_to_longlong():
    check(to_longlong, [int], (42,))

def test_uint_to_int():
    def uint_to_int(x):
        return intmask(x)
    check(uint_to_int, [r_uint], (sys.maxint+1,))

def test_float_to_int():
    check(to_int, [float], (42.5,))

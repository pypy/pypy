from pypy.translator.cli.test.runtest import check
from pypy.rpython.rarithmetic import r_uint, r_ulonglong, r_longlong

import sys

def test_op():
    yield check, op_any_ge, [int, int], (42, 42)
    yield check, op_any_ge, [int, int], (13, 42)    
    yield check, op_any_le, [int, int], (42, 42)
    yield check, op_any_le, [int, int], (13, 42)    
    
    for name, func in globals().iteritems():
        if not name.startswith('op_'):
            continue

        any = '_any_' in name
        if any or '_int_' in name:
            yield check, func, [int, int], (42, 13)

        if any or '_uint_' in name:
            yield check, func, [r_uint, r_uint], (r_uint(sys.maxint+1), r_uint(42))

        if any or '_long_' in name:
            yield check, func, [r_longlong, r_longlong], (r_longlong(sys.maxint*3), r_longlong(42))

        if any or '_ulong_' in name:
            yield check, func, [r_ulonglong, r_ulonglong], (r_ulonglong(sys.maxint*3), r_ulonglong(42))

        if any or '_float_' in name:
            yield check, func, [float, float], (42.0, (10.0/3))



def op_int_long_float_neg(x, y):
    return -x

def op_any_ge(x, y):
    return x>=y

def op_any_le(x, y):
    return x<=y

def op_int_float_and_not(x, y):
    return x and (not y)

def op_int_uint_shift(x, y):
    return x<<3 + y>>4

def op_int_uint_bitwise(x, y):
    return (x&y) | ~(x^y)

def op_int_long_uint_ulong_modulo(x, y):
    return x%y

def op_any_operations(x, y):
    return (x*y) + (x-y) + (x/y)

def op_any_abs(x, y):
    return abs(x)

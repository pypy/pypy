from pypy.translator.cli.test.runtest import CliTest
from pypy.translator.cli.test.runtest import check
from pypy.rpython.rarithmetic import r_uint, r_ulonglong, r_longlong, ovfcheck
from pypy.rpython import rstack
from pypy.annotation import model as annmodel
import sys

char = annmodel.SomeChar()

class TestOperations(CliTest):
    def test_div_zero(self):
        def fn(x, y):
            try:
                return x/y
            except ZeroDivisionError:
                return -1
        assert self.interpret(fn, [10, 0]) == -1

    def test_mod_ovf_zer(self):
        def fn(x, y):
            try:
                return ovfcheck(x % y)
            except OverflowError:
                return -1
            except ZeroDivisionError:
                return -2
        assert self.interpret(fn, [10, 3]) == 1
        assert self.interpret(fn, [10, 0]) == -2

    def test_llong_and(self):
        def fn(x, y):
            return x & y
        assert self.interpret(fn, [r_longlong(10), r_longlong(11)]) == 10

    def test_two_overflows(self):
        def fn(x, y):
            res = -42
            try:
                res = ovfcheck(x+y)
            except OverflowError:
                res = 0
            try:
                res += ovfcheck(x+y)
            except OverflowError:
                res += 1
            return res
        assert self.interpret(fn, [sys.maxint, 2]) == 1

    def test_ignore_resume_point(self):
        def fn(x):
            rstack.resume_point('hello world', x)
            return x
        assert self.interpret(fn, [42]) == 42

def test_op():
    yield check, op_any_ge, [int, int], (42, 42)
    yield check, op_any_ge, [int, int], (13, 42)
    yield check, op_any_le, [int, int], (42, 42)
    yield check, op_any_le, [int, int], (13, 42)

    yield check, op_any_eq, [char, char], ('a', 'a')
    yield check, op_any_ne, [char, char], ('a', 'b')
    yield check, op_any_ge, [char, char], ('a', 'b')
    yield check, op_any_ge, [char, char], ('b', 'a')
    yield check, op_any_le, [char, char], ('a', 'b')
    yield check, op_any_le, [char, char], ('b', 'a')

    yield check, op_unichar_eq, [int, int], (0, 0)
    yield check, op_unichar_ne, [int, int], (0, 1)

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

def op_unichar_eq(x, y):
    const = [u'\u03b1', u'\u03b2']
    return const[x] == const[y]

def op_unichar_ne(x, y):
    const = [u'\u03b1', u'\u03b2']
    return const[x] != const[y]


def op_any_eq(x, y):
    return x == y

def op_any_ne(x, y):
    return x != y

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

def op_any_is_true(x, y):
    return bool(x)

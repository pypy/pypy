from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.rlib.rarithmetic import r_uint, r_ulonglong, r_longlong, ovfcheck
from pypy.rlib import rstack
from pypy.annotation import model as annmodel
import sys

char = annmodel.SomeChar()

def fn_eq(x, y):
    return x == y

def fn_ne(x, y):
    return x != y

def fn_ge(x, y):
    return x>=y

def fn_le(x, y):
    return x<=y

class BaseTestOperations(object):
    FLOAT_PRECISION = 8

    def _check(self, fn, annotation, args):
        res1 = fn(*args)
        res2 = self.interpret(fn, args, annotation)
        if type(res1) is float:
            assert round(res1, self.FLOAT_PRECISION) == round(res2, self.FLOAT_PRECISION)
        else:
            assert res1 == res2

    def _check_int(self, f):
        self._check(f, [int, int], (42, 13))

    def _check_r_uint(self, f):
        self._check(f, [r_uint, r_uint], (r_uint(sys.maxint+1), r_uint(42)))

    def _check_r_longlong(self, f):
        self._check(f, [r_longlong, r_longlong], (r_longlong(sys.maxint*3), r_longlong(42)))

    def _check_r_ulonglong(self, f):
        self._check(f, [r_ulonglong, r_ulonglong], (r_ulonglong(sys.maxint*3), r_ulonglong(42)))
        
    def _check_float(self, f):
        self._check(f, [float, float], (42.0, (10.0/3)))

    def _check_all(self, fn):
        self._check_int(fn)
        self._check_r_uint(fn)
        self._check_r_longlong(fn)
        self._check_r_ulonglong(fn)
        self._check_float(fn)
    
    def test_div_zero(self):
        def fn(x, y):
            try:
                return x/y
            except ZeroDivisionError:
                return -1
        assert self.interpret(fn, [10, 0]) == -1

    def test_div_ovf_zer(self):
        def fn(x, y):
            try:
                return ovfcheck(x // y)
            except OverflowError:
                return -41
            except ZeroDivisionError:
                return -42
        assert self.interpret(fn, [50, 3]) == 16
        assert self.interpret(fn, [50, 0]) == -42
        assert self.interpret(fn, [50, -3]) == -17
        assert self.interpret(fn, [-50, 3]) == -17
        assert self.interpret(fn, [-50, -3]) == 16
        assert self.interpret(fn, [-sys.maxint-1, -1]) == -41
    
    def test_mod_ovf_zer(self):
        def fn(x, y):
            try:
                return ovfcheck(x % y)
            except OverflowError:
                return -41
            except ZeroDivisionError:
                return -42
        assert self.interpret(fn, [10, 3]) == 1
        assert self.interpret(fn, [10, 0]) == -42
        assert self.interpret(fn, [10, -3]) == -2
        assert self.interpret(fn, [-10, 3]) == 2
        assert self.interpret(fn, [-10, -3]) == -1
        assert self.interpret(fn, [-sys.maxint-1, -1]) == -41

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

    def test_rshift(self):
        def fn(x, y):
            return x >> y
        assert self.interpret(fn, [r_longlong(32), 1]) == 16

    def test_uint_neg(self):
        def fn(x):
            return -x
        self._check(fn, [r_uint], [r_uint(sys.maxint+1)])

    def test_unichar_eq(self):
        def fn(x, y):
            const = [u'\u03b1', u'\u03b2']
            return const[x] == const[y]
        self._check(fn, [int, int], (0, 0))

    def test_unichar_ne(self):
        def fn(x, y):
            const = [u'\u03b1', u'\u03b2']
            return const[x] != const[y]
        self._check(fn, [int, int], (0, 1))

    def test_int_le(self):
        self._check(fn_le, [int, int], (42, 42))
        self._check(fn_le, [int, int], (13, 42))

    def test_int_ge(self):
        self._check(fn_ge, [int, int], (42, 42))
        self._check(fn_ge, [int, int], (13, 42))

    def test_char_cmp(self):
        self._check(fn_eq, [char, char], ('a', 'a'))
        self._check(fn_ne, [char, char], ('a', 'b'))
        self._check(fn_ge, [char, char], ('a', 'b'))
        self._check(fn_ge, [char, char], ('b', 'a'))
        self._check(fn_le, [char, char], ('a', 'b'))
        self._check(fn_le, [char, char], ('b', 'a'))

    def test_eq(self):
        self._check_all(fn_eq)

    def test_ne(self):
        self._check_all(fn_ne)

    def test_neg(self):        
        def fn(x, y):
            return -x
        self._check_int(fn)
        self._check_r_longlong(fn)
        self._check_float(fn)
        
    def test_ge(self):
        self._check_all(fn_ge)

    def test_le(self):
        self._check_all(fn_le)

    def test_and_not(self):
        def fn(x, y):
            return x and (not y)
        self._check_int(fn)
        self._check_float(fn)

    def test_uint_shift(self):
        def fn(x, y):
            return x<<3 + y>>4
        self._check_r_uint(fn)

    def test_bitwise(self):
        def fn(x, y):
            return (x&y) | ~(x^y)
        self._check_int(fn)
        self._check_r_uint(fn)

    def test_modulo(self):
        def fn(x, y):
            return x%y
        self._check_int(fn)
        self._check_r_uint(fn)
        self._check_r_longlong(fn)        
        self._check_r_ulonglong(fn)

    def test_operations(self):
        def fn(x, y):
            return (x*y) + (x-y) + (x/y)
        self._check_all(fn)

    def test_abs(self):
        def fn(x, y):
            return abs(x)
        self._check_all(fn)

    def test_is_true(self):
        def fn(x, y):
            return bool(x)
        self._check_all(fn)

    def test_box(self):
        def f():
            x = 42
            y = llop.oobox_int(ootype.Object, x)
            return llop.oounbox_int(lltype.Signed, y)
        assert self.interpret(f, []) == 42

    def test_ullong_rshift(self):
        def f(x):
            return x >> 1
        x = sys.maxint+1
        assert self.interpret(f, [r_ulonglong(x)]) == x >> 1
        
    def test_compare_big_ullongs(self):
        bigval = r_ulonglong(9223372036854775808L)
        def fn(x):
            if x > bigval: return 1
            if x == bigval: return 0
            if x < bigval: return -1
            return -2
        
        for val in (bigval-1, bigval, bigval+1):
            expected = fn(val)
            res = self.interpret(fn, [val])
            assert res == expected

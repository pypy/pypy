import sys
from pypy.translator.translator import TranslationContext
from pypy.rpython.test import snippet
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin
from pypy.rlib.rarithmetic import (
    r_int, r_uint, r_longlong, r_ulonglong, r_singlefloat)
from pypy.rlib.objectmodel import compute_hash

class TestSnippet(object):

    def _test(self, func, types):
        t = TranslationContext()
        t.buildannotator().build_types(func, types)
        t.buildrtyper().specialize()
        t.checkgraphs()    
 
    def test_not1(self):
        self._test(snippet.not1, [float])

    def test_not2(self):
        self._test(snippet.not2, [float])

    def test_float1(self):
        self._test(snippet.float1, [float])

    def test_float_cast1(self):
        self._test(snippet.float_cast1, [float])

    def DONTtest_unary_operations(self):
        # XXX TODO test if all unary operations are implemented
        for opname in annmodel.UNARY_OPERATIONS:
            print 'UNARY_OPERATIONS:', opname

    def DONTtest_binary_operations(self):
        # XXX TODO test if all binary operations are implemented
        for opname in annmodel.BINARY_OPERATIONS:
            print 'BINARY_OPERATIONS:', opname

class BaseTestRfloat(BaseRtypingTest):

    inf = 'inf'
    minus_inf = '-inf'
    nan = 'nan'

    def test_float2str(self):
        def fn(f):
            return str(f)

        res = self.interpret(fn, [1.5])
        assert float(self.ll_to_string(res)) == 1.5
        res = self.interpret(fn, [-1.5])
        assert float(self.ll_to_string(res)) == -1.5
        inf = 1e200 * 1e200
        nan = inf/inf
        res = self.interpret(fn, [inf])
        assert self.ll_to_string(res) == self.inf
        res = self.interpret(fn, [-inf])
        assert self.ll_to_string(res) == self.minus_inf
        res = self.interpret(fn, [nan])
        assert self.ll_to_string(res) == self.nan

    def test_string_mod_float(self):
        def fn(f):
            return '%f' % f

        res = self.interpret(fn, [1.5])
        assert float(self.ll_to_string(res)) == 1.5

    def test_int_conversion(self):
        def fn(f):
            return int(f)

        res = self.interpret(fn, [1.0])
        assert res == 1
        assert type(res) is int 
        res = self.interpret(fn, [2.34])
        assert res == fn(2.34) 

    def test_longlong_conversion(self):
        def fn(f):
            return r_longlong(f)

        res = self.interpret(fn, [1.0])
        assert res == 1
        # r_longlong is int on a 64 bit system
        if sys.maxint == 2**63 - 1:
            assert self.is_of_type(res, int)
        else:
            assert self.is_of_type(res, r_longlong)
        res = self.interpret(fn, [2.34])
        assert res == fn(2.34) 
        big = float(0x7fffffffffffffff)
        x = big - 1.e10
        assert x != big
        y = fn(x)
        assert fn(x) == 9223372026854775808

    def test_to_r_uint(self):
        def fn(x):
            return r_uint(x)

        res = self.interpret(fn, [12.34])
        assert res == 12
        bigval = sys.maxint * 1.234
        res = self.interpret(fn, [bigval])
        assert long(res) == long(bigval)

    def test_from_r_uint(self):
        def fn(n):
            return float(r_uint(n)) / 2

        res = self.interpret(fn, [41])
        assert self.float_eq(res, 20.5)
        res = self.interpret(fn, [-9])
        assert self.float_eq(res, 0.5 * ((sys.maxint+1)*2 - 9))

    def test_to_r_ulonglong(self):
        def fn(x):
            return r_ulonglong(x)
        res = self.interpret(fn, [12.34])
        assert res == 12
        bigval = sys.maxint * 1.234
        res = self.interpret(fn, [bigval])
        assert long(res) == long(bigval)

    def test_from_r_ulonglong(self):
        def fn(n):
            return float(r_ulonglong(n)) / 2
        res = self.interpret(fn, [41])
        assert self.float_eq(res, 20.5)

    def test_r_singlefloat(self):
        def fn(x):
            y = r_singlefloat(x)
            return float(y)

        res = self.interpret(fn, [2.1])
        assert res != 2.1     # precision lost
        assert abs(res - 2.1) < 1E-6

    def test_float_constant_conversions(self):
        DIV = r_longlong(10 ** 10)
        def fn():
            return 420000000000.0 / DIV

        res = self.interpret(fn, [])
        assert self.float_eq(res, 42.0)

    def test_exceptions(self):
        def fn(x, y, z):
            try:
                # '/', when float-based, cannot raise in RPython!
                # the try:finally: only tests an annotation bug.
                x /= (y / z)
            finally:
                return x
        self.interpret(fn, [1.0, 2.0, 3.0])

    def test_copysign(self):
        from pypy.rlib import rfloat
        def fn(x, y):
            return rfloat.copysign(x, y)
        assert self.interpret(fn, [42, -1]) == -42
        assert self.interpret(fn, [42, -0.0]) == -42
        assert self.interpret(fn, [42, 0.0]) == 42

    def test_rstring_to_float(self):
        from pypy.rlib.rfloat import rstring_to_float
        def fn(i):
            s = ['42.3', '123.4'][i]
            return rstring_to_float(s)
        assert self.interpret(fn, [0]) == 42.3

    def test_isnan(self):
        from pypy.rlib import rfloat
        def fn(x, y):
            n1 = x * x
            n2 = y * y * y
            return rfloat.isnan(n1 / n2)
        if self.__class__.__name__ != 'TestCliFloat':
            # the next line currently fails on mono 2.6.7 (ubuntu 11.04), see:
            # https://bugzilla.novell.com/show_bug.cgi?id=692493
            assert self.interpret(fn, [1e200, 1e200])   # nan
        #
        assert not self.interpret(fn, [1e200, 1.0])   # +inf
        assert not self.interpret(fn, [1e200, -1.0])  # -inf
        assert not self.interpret(fn, [42.5, 2.3])    # +finite
        assert not self.interpret(fn, [42.5, -2.3])   # -finite

    def test_isinf(self):
        from pypy.rlib import rfloat
        def fn(x, y):
            n1 = x * x
            n2 = y * y * y
            return rfloat.isinf(n1 / n2)
        assert self.interpret(fn, [1e200, 1.0])       # +inf
        assert self.interpret(fn, [1e200, -1.0])      # -inf
        assert not self.interpret(fn, [1e200, 1e200]) # nan
        assert not self.interpret(fn, [42.5, 2.3])    # +finite
        assert not self.interpret(fn, [42.5, -2.3])   # -finite

    def test_isfinite(self):
        from pypy.rlib import rfloat
        def fn(x, y):
            n1 = x * x
            n2 = y * y * y
            return rfloat.isfinite(n1 / n2)
        assert self.interpret(fn, [42.5, 2.3])        # +finite
        assert self.interpret(fn, [42.5, -2.3])       # -finite
        assert not self.interpret(fn, [1e200, 1.0])   # +inf
        assert not self.interpret(fn, [1e200, -1.0])  # -inf
        #
        if self.__class__.__name__ != 'TestCliFloat':
            # the next line currently fails on mono 2.6.7 (ubuntu 11.04), see:
            # https://bugzilla.novell.com/show_bug.cgi?id=692493
            assert not self.interpret(fn, [1e200, 1e200]) # nan

    def test_break_up_float(self):
        from pypy.rlib.rfloat import break_up_float
        assert break_up_float('1') == ('', '1', '', '')
        assert break_up_float('+1') == ('+', '1', '', '')
        assert break_up_float('-1') == ('-', '1', '', '')

        assert break_up_float('.5') == ('', '', '5', '')

        assert break_up_float('1.2e3') == ('', '1', '2', '3')
        assert break_up_float('1.2e+3') == ('', '1', '2', '+3')
        assert break_up_float('1.2e-3') == ('', '1', '2', '-3')

        # some that will get thrown out on return:
        assert break_up_float('.') == ('', '', '', '')
        assert break_up_float('+') == ('+', '', '', '')
        assert break_up_float('-') == ('-', '', '', '')
        assert break_up_float('e1') == ('', '', '', '1')

        raises(ValueError, break_up_float, 'e')

    def test_formatd(self):
        from pypy.rlib.rfloat import formatd
        def f(x):
            return formatd(x, 'f', 2, 0)
        res = self.ll_to_string(self.interpret(f, [10/3.0]))
        assert res == '3.33'

    def test_formatd_repr(self):
        from pypy.rlib.rfloat import formatd
        def f(x):
            return formatd(x, 'r', 0, 0)
        res = self.ll_to_string(self.interpret(f, [1.1]))
        assert res == '1.1'

    def test_formatd_huge(self):
        from pypy.rlib.rfloat import formatd
        def f(x):
            return formatd(x, 'f', 1234, 0)
        res = self.ll_to_string(self.interpret(f, [1.0]))
        assert res == '1.' + 1234 * '0'

    def test_formatd_F(self):
        from pypy.translator.c.test.test_genc import compile
        from pypy.rlib.rfloat import formatd

        def func(x):
            # Test the %F format, which is not supported by
            # the Microsoft's msvcrt library.
            return formatd(x, 'F', 4)

        f = compile(func, [float])
        assert f(10/3.0) == '3.3333'

    def test_parts_to_float(self):
        from pypy.rlib.rfloat import parts_to_float, break_up_float
        def f(x):
            if x == 0:
                s = '1.0'
            else:
                s = '1e-100'
            sign, beforept, afterpt, expt = break_up_float(s)
            return parts_to_float(sign, beforept, afterpt, expt)
        res = self.interpret(f, [0])
        assert res == 1.0

        res = self.interpret(f, [1])
        assert res == 1e-100

    def test_string_to_float(self):
        from pypy.rlib.rfloat import rstring_to_float
        def func(x):
            if x == 0:
                s = '1e23'
            else:
                s = '-1e23'
            return rstring_to_float(s)

        assert self.interpret(func, [0]) == 1e23
        assert self.interpret(func, [1]) == -1e23

    def test_copysign(self):
        from pypy.rlib.rfloat import copysign
        assert copysign(1, 1) == 1
        assert copysign(-1, 1) == 1
        assert copysign(-1, -1) == -1
        assert copysign(1, -1) == -1
        assert copysign(1, -0.) == -1

    def test_round_away(self):
        from pypy.rlib.rfloat import round_away
        assert round_away(.1) == 0.
        assert round_away(.5) == 1.
        assert round_away(.7) == 1.
        assert round_away(1.) == 1.
        assert round_away(-.5) == -1.
        assert round_away(-.1) == 0.
        assert round_away(-.7) == -1.
        assert round_away(0.) == 0.

    def test_round_double(self):
        from pypy.rlib.rfloat import round_double
        def almost_equal(x, y):
            assert round(abs(x-y), 7) == 0

        almost_equal(round_double(0.125, 2), 0.13)
        almost_equal(round_double(0.375, 2), 0.38)
        almost_equal(round_double(0.625, 2), 0.63)
        almost_equal(round_double(0.875, 2), 0.88)
        almost_equal(round_double(-0.125, 2), -0.13)
        almost_equal(round_double(-0.375, 2), -0.38)
        almost_equal(round_double(-0.625, 2), -0.63)
        almost_equal(round_double(-0.875, 2), -0.88)

        almost_equal(round_double(0.25, 1), 0.3)
        almost_equal(round_double(0.75, 1), 0.8)
        almost_equal(round_double(-0.25, 1), -0.3)
        almost_equal(round_double(-0.75, 1), -0.8)

        round_double(-6.5, 0) == -7.0
        round_double(-5.5, 0) == -6.0
        round_double(-1.5, 0) == -2.0
        round_double(-0.5, 0) == -1.0
        round_double(0.5, 0) == 1.0
        round_double(1.5, 0) == 2.0
        round_double(2.5, 0) == 3.0
        round_double(3.5, 0) == 4.0
        round_double(4.5, 0) == 5.0
        round_double(5.5, 0) == 6.0
        round_double(6.5, 0) == 7.0

        round_double(-25.0, -1) == -30.0
        round_double(-15.0, -1) == -20.0
        round_double(-5.0, -1) == -10.0
        round_double(5.0, -1) == 10.0
        round_double(15.0, -1) == 20.0
        round_double(25.0, -1) == 30.0
        round_double(35.0, -1) == 40.0
        round_double(45.0, -1) == 50.0
        round_double(55.0, -1) == 60.0
        round_double(65.0, -1) == 70.0
        round_double(75.0, -1) == 80.0
        round_double(85.0, -1) == 90.0
        round_double(95.0, -1) == 100.0
        round_double(12325.0, -1) == 12330.0

        round_double(350.0, -2) == 400.0
        round_double(450.0, -2) == 500.0

        almost_equal(round_double(0.5e21, -21), 1e21)
        almost_equal(round_double(1.5e21, -21), 2e21)
        almost_equal(round_double(2.5e21, -21), 3e21)
        almost_equal(round_double(5.5e21, -21), 6e21)
        almost_equal(round_double(8.5e21, -21), 9e21)

        almost_equal(round_double(-1.5e22, -22), -2e22)
        almost_equal(round_double(-0.5e22, -22), -1e22)
        almost_equal(round_double(0.5e22, -22), 1e22)
        almost_equal(round_double(1.5e22, -22), 2e22)


class TestLLtype(BaseTestRfloat, LLRtypeMixin):

    def test_hash(self):
        def fn(f):
            return compute_hash(f)
        res = self.interpret(fn, [1.5])
        assert res == compute_hash(1.5)


class TestOOtype(BaseTestRfloat, OORtypeMixin):

    def test_formatd(self):
        skip('formatd is broken on ootype')

    def test_formatd_repr(self):
        skip('formatd is broken on ootype')

    def test_formatd_huge(self):
        skip('formatd is broken on ootype')

    def test_string_to_float(self):
        skip('string_to_float is broken on ootype')

from __future__ import with_statement

import py
from pypy.interpreter.function import Function
from pypy.interpreter.gateway import BuiltinCode
from pypy.module.math.test import test_direct


class AppTestMath:
    spaceconfig = {
        "usemodules": ['math', 'struct', 'itertools', 'time', 'binascii'],
    }

    def setup_class(cls):
        space = cls.space
        cases = []
        for a, b, expected in test_direct.MathTests.TESTCASES:
            if type(expected) is type and issubclass(expected, Exception):
                expected = getattr(space, "w_%s" % expected.__name__)
            elif callable(expected):
                if not cls.runappdirect:
                    expected = cls.make_callable_wrapper(expected)
            else:
                expected = space.wrap(expected)
            cases.append(space.newtuple([space.wrap(a), space.wrap(b), expected]))
        cls.w_cases = space.newlist(cases)
        cls.w_consistent_host = space.wrap(test_direct.consistent_host)

    @classmethod
    def make_callable_wrapper(cls, func):
        def f(space, w_x):
            return space.wrap(func(space.unwrap(w_x)))
        return Function(cls.space, BuiltinCode(f))

    def w_ftest(self, actual, expected):
        assert abs(actual - expected) < 10E-5

    def test_all_cases(self):
        if not self.consistent_host:
            skip("please test this on top of PyPy or CPython >= 2.6")
        import math
        for fnname, args, expected in self.cases:
            fn = getattr(math, fnname)
            print fn, args
            try:
                got = fn(*args)
            except ValueError:
                assert expected == ValueError
            except OverflowError:
                assert expected == OverflowError
            else:
                if type(expected) is type(Exception):
                    ok = False
                elif callable(expected):
                    ok = expected(got)
                else:
                    gotsign = expectedsign = 1
                    if got < 0.0: gotsign = -gotsign
                    if expected < 0.0: expectedsign = -expectedsign
                    ok = got == expected and gotsign == expectedsign
                if not ok:
                    raise AssertionError("%s(%s): got %s" % (
                        fnname, ', '.join(map(str, args)), got))

    def test_ldexp(self):
        import math
        assert math.ldexp(float("inf"), -10**20) == float("inf")

    def test_fsum(self):
        import math

        # detect evidence of double-rounding: fsum is not always correctly
        # rounded on machines that suffer from double rounding.
        # It is a known problem with IA32 floating-point arithmetic.
        # It should work fine e.g. with x86-64.
        x, y = 1e16, 2.9999 # use temporary values to defeat peephole optimizer
        HAVE_DOUBLE_ROUNDING = (x + y == 1e16 + 4)
        if HAVE_DOUBLE_ROUNDING:
            skip("fsum is not exact on machines with double rounding")

        test_values = [
            ([], 0.0),
            ([0.0], 0.0),
            ([1e100, 1.0, -1e100, 1e-100, 1e50, -1.0, -1e50], 1e-100),
            ([2.0**53, -0.5, -2.0**-54], 2.0**53-1.0),
            ([2.0**53, 1.0, 2.0**-100], 2.0**53+2.0),
            ([2.0**53+10.0, 1.0, 2.0**-100], 2.0**53+12.0),
            ([2.0**53-4.0, 0.5, 2.0**-54], 2.0**53-3.0),
            ([1./n for n in range(1, 1001)],
             float.fromhex('0x1.df11f45f4e61ap+2')),
            ([(-1.)**n/n for n in range(1, 1001)],
             float.fromhex('-0x1.62a2af1bd3624p-1')),
            ([1.7**(i+1)-1.7**i for i in range(1000)] + [-1.7**1000], -1.0),
            ([1e16, 1., 1e-16], 10000000000000002.0),
            ([1e16-2., 1.-2.**-53, -(1e16-2.), -(1.-2.**-53)], 0.0),
            # exercise code for resizing partials array
            ([2.**n - 2.**(n+50) + 2.**(n+52) for n in range(-1074, 972, 2)] +
             [-2.**1022],
             float.fromhex('0x1.5555555555555p+970')),
            # infinity and nans
            ([float("inf")], float("inf")),
            ([float("-inf")], float("-inf")),
            ([float("nan")], float("nan")),
            ]

        for i, (vals, expected) in enumerate(test_values):
            try:
                actual = math.fsum(vals)
            except OverflowError:
                py.test.fail("test %d failed: got OverflowError, expected %r "
                          "for math.fsum(%.100r)" % (i, expected, vals))
            except ValueError:
                py.test.fail("test %d failed: got ValueError, expected %r "
                          "for math.fsum(%.100r)" % (i, expected, vals))
            assert actual == expected or (
                math.isnan(actual) and math.isnan(expected))

    def test_factorial(self):
        import math
        assert math.factorial(0) == 1
        assert math.factorial(1) == 1
        assert math.factorial(2) == 2
        assert math.factorial(5) == 120
        assert math.factorial(5.) == 120
        raises(ValueError, math.factorial, -1)
        raises(ValueError, math.factorial, -1.)
        raises(ValueError, math.factorial, 1.1)

    def test_log1p(self):
        import math
        self.ftest(math.log1p(1/math.e-1), -1)
        self.ftest(math.log1p(0), 0)
        self.ftest(math.log1p(math.e-1), 1)
        self.ftest(math.log1p(1), math.log(2))

    def test_acosh(self):
        import math
        self.ftest(math.acosh(1), 0)
        self.ftest(math.acosh(2), 1.3169578969248168)
        assert math.isinf(math.asinh(float("inf")))
        raises(ValueError, math.acosh, 0)

    def test_asinh(self):
        import math
        self.ftest(math.asinh(0), 0)
        self.ftest(math.asinh(1), 0.88137358701954305)
        self.ftest(math.asinh(-1), -0.88137358701954305)
        assert math.isinf(math.asinh(float("inf")))

    def test_atanh(self):
        import math
        self.ftest(math.atanh(0), 0)
        self.ftest(math.atanh(0.5), 0.54930614433405489)
        self.ftest(math.atanh(-0.5), -0.54930614433405489)
        raises(ValueError, math.atanh, 1.)
        assert math.isnan(math.atanh(float("nan")))

    def test_trunc(self):
        import math
        assert math.trunc(1.9) == 1.0
        raises((AttributeError, TypeError), math.trunc, 1.9j)
        class foo(object):
            def __trunc__(self):
                return "truncated"
        assert math.trunc(foo()) == "truncated"

    def test_copysign_nan(self):
        skip('sign of nan is undefined')
        import math
        assert math.copysign(1.0, float('-nan')) == -1.0

    def test_erf(self):
        import math
        assert math.erf(100.0) == 1.0
        assert math.erf(-1000.0) == -1.0
        assert math.erf(float("inf")) == 1.0
        assert math.erf(float("-inf")) == -1.0
        assert math.isnan(math.erf(float("nan")))
        # proper tests are in rpython/rlib/test/test_rfloat
        assert round(math.erf(1.0), 9) == 0.842700793

    def test_erfc(self):
        import math
        assert math.erfc(0.0) == 1.0
        assert math.erfc(-0.0) == 1.0
        assert math.erfc(float("inf")) == 0.0
        assert math.erfc(float("-inf")) == 2.0
        assert math.isnan(math.erf(float("nan")))
        assert math.erfc(1e-308) == 1.0

    def test_gamma(self):
        import math
        assert raises(ValueError, math.gamma, 0.0)
        assert math.gamma(5.0) == 24.0
        assert math.gamma(6.0) == 120.0
        assert raises(ValueError, math.gamma, -1)
        assert math.gamma(0.5) == math.pi ** 0.5

    def test_lgamma(self):
        import math
        math.lgamma(1.0) == 0.0
        math.lgamma(2.0) == 0.0
        # proper tests are in rpython/rlib/test/test_rfloat
        assert round(math.lgamma(5.0), 9) == round(math.log(24.0), 9)
        assert round(math.lgamma(6.0), 9) == round(math.log(120.0), 9)
        assert raises(ValueError, math.gamma, -1)
        assert round(math.lgamma(0.5), 9) == round(math.log(math.pi ** 0.5), 9)

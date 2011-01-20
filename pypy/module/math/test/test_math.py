import sys
from pypy.conftest import gettestobjspace
from pypy.module.math.test import test_direct


class AppTestMath:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['math'])
        cls.w_cases = cls.space.wrap(test_direct.MathTests.TESTCASES)
        cls.w_consistent_host = cls.space.wrap(test_direct.consistent_host)

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
            assert actual == expected

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

    def test_mtestfile(self):
        import math
        import abc
        import os
        import struct
        def _parse_mtestfile(fname):
            """Parse a file with test values

            -- starts a comment
            blank lines, or lines containing only a comment, are ignored
            other lines are expected to have the form
              id fn arg -> expected [flag]*

            """
            with open(fname) as fp:
                for line in fp:
                    # strip comments, and skip blank lines
                    if '--' in line:
                        line = line[:line.index('--')]
                    if not line.strip():
                        continue

                    lhs, rhs = line.split('->')
                    id, fn, arg = lhs.split()
                    rhs_pieces = rhs.split()
                    exp = rhs_pieces[0]
                    flags = rhs_pieces[1:]

                    yield (id, fn, float(arg), float(exp), flags)
        def to_ulps(x):
            """Convert a non-NaN float x to an integer, in such a way that
            adjacent floats are converted to adjacent integers.  Then
            abs(ulps(x) - ulps(y)) gives the difference in ulps between two
            floats.

            The results from this function will only make sense on platforms
            where C doubles are represented in IEEE 754 binary64 format.

            """
            n = struct.unpack('<q', struct.pack('<d', x))[0]
            if n < 0:
                n = ~(n+2**63)
            return n

        def ulps_check(expected, got, ulps=20):
            """Given non-NaN floats `expected` and `got`,
            check that they're equal to within the given number of ulps.

            Returns None on success and an error message on failure."""

            ulps_error = to_ulps(got) - to_ulps(expected)
            if abs(ulps_error) <= ulps:
                return None
            return "error = {} ulps; permitted error = {} ulps".format(ulps_error,
                                                                       ulps)

        def acc_check(expected, got, rel_err=2e-15, abs_err = 5e-323):
            """Determine whether non-NaN floats a and b are equal to within a
            (small) rounding error.  The default values for rel_err and
            abs_err are chosen to be suitable for platforms where a float is
            represented by an IEEE 754 double.  They allow an error of between
            9 and 19 ulps."""

            # need to special case infinities, since inf - inf gives nan
            if math.isinf(expected) and got == expected:
                return None

            error = got - expected

            permitted_error = max(abs_err, rel_err * abs(expected))
            if abs(error) < permitted_error:
                return None
            return "error = {}; permitted error = {}".format(error,
                                                             permitted_error)

        ALLOWED_ERROR = 20  # permitted error, in ulps
        fail_fmt = "{}:{}({!r}): expected {!r}, got {!r}"

        failures = []
        math_testcases = os.path.join(os.path.dirname(abc.__file__), "test",
                                      "math_testcases.txt")
        for id, fn, arg, expected, flags in _parse_mtestfile(math_testcases):
            func = getattr(math, fn)

            if 'invalid' in flags or 'divide-by-zero' in flags:
                expected = 'ValueError'
            elif 'overflow' in flags:
                expected = 'OverflowError'

            try:
                got = func(arg)
            except ValueError:
                got = 'ValueError'
            except OverflowError:
                got = 'OverflowError'

            accuracy_failure = None
            if isinstance(got, float) and isinstance(expected, float):
                if math.isnan(expected) and math.isnan(got):
                    continue
                if not math.isnan(expected) and not math.isnan(got):
                    if fn == 'lgamma':
                        # we use a weaker accuracy test for lgamma;
                        # lgamma only achieves an absolute error of
                        # a few multiples of the machine accuracy, in
                        # general.
                        accuracy_failure = acc_check(expected, got,
                                                  rel_err = 5e-15,
                                                  abs_err = 5e-15)
                    elif fn == 'erfc':
                        # erfc has less-than-ideal accuracy for large
                        # arguments (x ~ 25 or so), mainly due to the
                        # error involved in computing exp(-x*x).
                        #
                        # XXX Would be better to weaken this test only
                        # for large x, instead of for all x.
                        accuracy_failure = ulps_check(expected, got, 2000)

                    else:
                        accuracy_failure = ulps_check(expected, got, 20)
                    if accuracy_failure is None:
                        continue

            if isinstance(got, str) and isinstance(expected, str):
                if got == expected:
                    continue

            fail_msg = fail_fmt.format(id, fn, arg, expected, got)
            if accuracy_failure is not None:
                fail_msg += ' ({})'.format(accuracy_failure)
            failures.append(fail_msg)
        assert not failures

    def test_trunc(self):
        import math
        assert math.trunc(1.9) == 1.0
        raises((AttributeError, TypeError), math.trunc, 1.9j)
        class foo(object):
            def __trunc__(self):
                return "truncated"
        assert math.trunc(foo()) == "truncated"

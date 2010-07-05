import sys
from pypy.conftest import gettestobjspace
from pypy.module.math.test import test_direct


class AppTestMath:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['math'])
        cls.w_cases = cls.space.wrap(test_direct.MathTests.TESTCASES)
        cls.w_consistent_host = cls.space.wrap(test_direct.consistent_host)

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

    def test_fsum(self):
        # Python version of math.fsum, for comparison.  Uses a
        # different algorithm based on frexp, ldexp and integer
        # arithmetic.
        import math

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

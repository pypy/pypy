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

import sys
from pypy.conftest import gettestobjspace
from pypy.module.math.test import test_direct


class AppTestMath:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['math'])
        cls.w_cases = cls.space.wrap(test_direct.MathTests.TESTCASES)
        cls.w_consistent = cls.space.wrap(test_direct.consistent)

    def test_all_cases(self):
        import math
        for fnname, args, expected in self.cases:
            fn = getattr(math, fnname)
            print fn, args
            try:
                got = fn(*args)
            except ValueError:
                assert expected == ValueError
            except OverflowError:
                if not self.consistent:
                    if expected == ValueError:
                        continue      # e.g. for 'log'
                    if callable(expected):
                        continue      # e.g. for 'ceil'
                assert expected == OverflowError
            else:
                if callable(expected):
                    ok = expected(got)
                else:
                    gotsign = expectedsign = 1
                    if got < 0.0: gotsign = -gotsign
                    if expected < 0.0: expectedsign = -expectedsign
                    ok = got == expected and gotsign == expectedsign
                if not ok:
                    raise AssertionError("%r: got %s" % (repr, got))

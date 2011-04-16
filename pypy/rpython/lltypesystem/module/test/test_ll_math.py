""" Try to test systematically all cases of ll_math.py.
"""

from pypy.rpython.lltypesystem.module import ll_math
from pypy.module.math.test.test_direct import MathTests, get_tester
from pypy.translator.c.test.test_genc import compile


class TestMath(MathTests):
    def test_isinf(self):
        inf = 1e200 * 1e200
        nan = inf / inf
        assert not ll_math.ll_math_isinf(0)
        assert ll_math.ll_math_isinf(inf)
        assert ll_math.ll_math_isinf(-inf)
        assert not ll_math.ll_math_isinf(nan)

    def test_isnan(self):
        inf = 1e200 * 1e200
        nan = inf / inf
        assert not ll_math.ll_math_isnan(0)
        assert ll_math.ll_math_isnan(nan)
        assert not ll_math.ll_math_isnan(inf)

    def test_compiled_isinf(self):
        def f(x):
            return ll_math.ll_math_isinf(1. / x)
        f = compile(f, [float], backendopt=False)
        assert f(5.5e-309)


def make_test_case((fnname, args, expected), dict):
    #
    def test_func(self):
        fn = getattr(ll_math, 'll_math_' + fnname)
        repr = "%s(%s)" % (fnname, ', '.join(map(str, args)))
        try:
            got = fn(*args)
        except ValueError:
            assert expected == ValueError, "%s: got a ValueError" % (repr,)
        except OverflowError:
            assert expected == OverflowError, "%s: got an OverflowError" % (
                repr,)
        else:
            if not get_tester(expected)(got):
                raise AssertionError("%r: got %r, expected %r" %
                                     (repr, got, expected))
    #
    dict[fnname] = dict.get(fnname, 0) + 1
    testname = 'test_%s_%d' % (fnname, dict[fnname])
    test_func.func_name = testname
    setattr(TestMath, testname, test_func)

_d = {}
for testcase in TestMath.TESTCASES:
    make_test_case(testcase, _d)

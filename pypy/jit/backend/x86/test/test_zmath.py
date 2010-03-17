""" Test that the math module still behaves even when
    compiled to C with SSE2 enabled.
"""
import py, math
from pypy.module.math.test import test_direct
from pypy.translator.c.test.test_genc import compile
from pypy.jit.backend.x86.codebuf import ensure_sse2_floats


def get_test_case((fnname, args, expected)):
    fn = getattr(math, fnname)
    expect_valueerror = (expected == ValueError)
    expect_overflowerror = (expected == OverflowError)
    check = test_direct.get_tester(expected)
    #
    def testfn():
        try:
            got = fn(*args)
        except ValueError:
            return expect_valueerror
        except OverflowError:
            return expect_overflowerror
        else:
            return check(got)
    #
    testfn.func_name = 'test_' + fnname
    return testfn


testfnlist = [get_test_case(testcase)
              for testcase in test_direct.MathTests.TESTCASES]

def fn():
    ensure_sse2_floats()
    for i in range(len(testfnlist)):
        testfn = testfnlist[i]
        if not testfn():
            return i
    return -42  # ok

def test_math():
    f = compile(fn, [])
    res = f()
    if res >= 0:
        py.test.fail(repr(test_direct.MathTests.TESTCASES[res]))
    else:
        assert res == -42

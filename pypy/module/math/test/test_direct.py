""" Try to test systematically all cases of the math module.
"""

import py, sys, math
from rpython.rlib import rfloat
from rpython.rtyper.lltypesystem.module.test.math_cases import (MathTests,
                                                                get_tester)

consistent_host = True
if '__pypy__' not in sys.builtin_module_names:
    if sys.version_info < (2, 6):
        consistent_host = False

class TestDirect(MathTests):
    pass

def do_test(fn, fnname, args, expected):
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
            raise AssertionError("%r: got %s" % (repr, got))

def make_test_case((fnname, args, expected), dict):
    #
    def test_func(self):
        if not consistent_host:
            py.test.skip("inconsistent behavior before 2.6")
        try:
            fn = getattr(math, fnname)
        except AttributeError:
            fn = getattr(rfloat, fnname)
        do_test(fn, fnname, args, expected)
    #
    dict[fnname] = dict.get(fnname, 0) + 1
    testname = 'test_%s_%d' % (fnname, dict[fnname])
    test_func.func_name = testname
    setattr(TestDirect, testname, test_func)

_d = {}
for testcase in TestDirect.TESTCASES:
    make_test_case(testcase, _d)

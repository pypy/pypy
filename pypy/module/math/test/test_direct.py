""" Try to test systematically all cases of the math module.
"""

import py, sys, math
from pypy.rlib import rfloat
from pypy.rlib.rfloat import isinf, isnan, INFINITY, NAN

consistent_host = True
if '__pypy__' not in sys.builtin_module_names:
    if sys.version_info < (2, 6):
        consistent_host = False

def positiveinf(x):
    return isinf(x) and x > 0.0

def negativeinf(x):
    return isinf(x) and x < 0.0

def finite(x):
    return not isinf(x) and not isnan(x)


unary_math_functions = ['acos', 'asin', 'atan',
                        'ceil', 'cos', 'cosh', 'exp', 'fabs', 'floor',
                        'sin', 'sinh', 'sqrt', 'tan', 'tanh', 'log', 'log10',
                        'acosh', 'asinh', 'atanh', 'log1p', 'expm1']
binary_math_functions = ['atan2', 'fmod', 'hypot', 'pow']


class MathTests:

    REGCASES = []
    for name in unary_math_functions:
        try:
            input, output = (0.3,), getattr(math, name)(0.3)
        except AttributeError:
            # cannot test this function
            continue
        except ValueError:
            input, output = (1.3,), getattr(math, name)(1.3)
        REGCASES.append((name, input, output))

    IRREGCASES = [
        ('atan2', (0.31, 0.123), math.atan2(0.31, 0.123)),
        ('fmod',  (0.31, 0.123), math.fmod(0.31, 0.123)),
        ('hypot', (0.31, 0.123), math.hypot(0.31, 0.123)),
        ('pow',   (0.31, 0.123), math.pow(0.31, 0.123)),
        ('pow',   (-0.31, 0.123), ValueError),
        ('pow',   (-0.5, 2.0), 0.25),
        ('pow',   (-0.5, 1.0), -0.5),
        ('pow',   (-0.5, 0.0), 1.0),
        ('pow',   (-0.5, -1.0), -2.0),
        ('ldexp', (3.375, 2), 13.5),
        ('ldexp', (1.0, -10000), 0.0),   # underflow
        ('frexp', (-1.25,), lambda x: x == (-0.625, 1)),
        ('modf',  (4.25,), lambda x: x == (0.25, 4.0)),
        ('modf',  (-4.25,), lambda x: x == (-0.25, -4.0)),
        ]

    OVFCASES = [
        ('cosh', (9999.9,), OverflowError),
        ('sinh', (9999.9,), OverflowError),
        ('exp', (9999.9,), OverflowError),
        ('pow', (10.0, 40000.0), OverflowError),
        ('ldexp', (10.0, 40000), OverflowError),
        ('log', (0.0,), ValueError),
        ('log', (-1.,), ValueError),
        ('log10', (0.0,), ValueError),
        ]

    INFCASES = [
        ('acos', (INFINITY,), ValueError),
        ('acos', (-INFINITY,), ValueError),
        ('asin', (INFINITY,), ValueError),
        ('asin', (-INFINITY,), ValueError),
        ('atan', (INFINITY,), math.pi / 2),
        ('atan', (-INFINITY,), -math.pi / 2),
        ('atanh', (INFINITY,), ValueError),
        ('atanh', (-INFINITY,), ValueError),
        ('ceil', (INFINITY,), positiveinf),
        ('ceil', (-INFINITY,), negativeinf),
        ('cos', (INFINITY,), ValueError),
        ('cos', (-INFINITY,), ValueError),
        ('cosh', (INFINITY,), positiveinf),
        ('cosh', (-INFINITY,), positiveinf),
        ('exp', (INFINITY,), positiveinf),
        ('exp', (-INFINITY,), 0.0),
        ('fabs', (INFINITY,), positiveinf),
        ('fabs', (-INFINITY,), positiveinf),
        ('floor', (INFINITY,), positiveinf),
        ('floor', (-INFINITY,), negativeinf),
        ('sin', (INFINITY,), ValueError),
        ('sin', (-INFINITY,), ValueError),
        ('sinh', (INFINITY,), positiveinf),
        ('sinh', (-INFINITY,), negativeinf),
        ('sqrt', (INFINITY,), positiveinf),
        ('sqrt', (-INFINITY,), ValueError),
        ('tan', (INFINITY,), ValueError),
        ('tan', (-INFINITY,), ValueError),
        ('tanh', (INFINITY,), 1.0),
        ('tanh', (-INFINITY,), -1.0),
        ('log', (INFINITY,), positiveinf),
        ('log', (-INFINITY,), ValueError),
        ('log10', (INFINITY,), positiveinf),
        ('log10', (-INFINITY,), ValueError),
        ('frexp', (INFINITY,), lambda x: isinf(x[0])),
        ('ldexp', (INFINITY, 3), positiveinf),
        ('ldexp', (-INFINITY, 3), negativeinf),
        ('modf',  (INFINITY,), lambda x: positiveinf(x[1])),
        ('modf',  (-INFINITY,), lambda x: negativeinf(x[1])),
        ('pow', (INFINITY, 0.0), 1.0),
        ('pow', (INFINITY, 0.001), positiveinf),
        ('pow', (INFINITY, -0.001), 0.0),
        ('pow', (-INFINITY, 0.0), 1.0),
        ('pow', (-INFINITY, 0.001), positiveinf),
        ('pow', (-INFINITY, -0.001), 0.0),
        ('pow', (-INFINITY, 3.0), negativeinf),
        ('pow', (-INFINITY, 6.0), positiveinf),
        ('pow', (-INFINITY, -13.0), -0.0),
        ('pow', (-INFINITY, -128.0), 0.0),
        ('pow', (1.001, INFINITY), positiveinf),
        ('pow', (1.0,   INFINITY), 1.0),
        ('pow', (0.999, INFINITY), 0.0),
        ('pow', (-0.999,INFINITY), 0.0),
        #('pow', (-1.0, INFINITY), 1.0, but strange, could also be -1.0),
        ('pow', (-1.001,INFINITY), positiveinf),
        ('pow', (1.001, -INFINITY), 0.0),
        ('pow', (1.0,   -INFINITY), 1.0),
        #('pow', (0.999, -INFINITY), positiveinf, but get OverflowError),
        #('pow', (INFINITY, INFINITY), positiveinf, but get OverflowError),
        ('pow', (INFINITY, -INFINITY), 0.0),
        ('pow', (-INFINITY, INFINITY), positiveinf),
        ]

    IRREGERRCASES = [
        #
        ('atan2', (INFINITY, -2.3), math.pi / 2),
        ('atan2', (INFINITY, 0.0), math.pi / 2),
        ('atan2', (INFINITY, 3.0), math.pi / 2),
        #('atan2', (INFINITY, INFINITY), ?strange),
        ('atan2', (2.1, INFINITY), 0.0),
        ('atan2', (0.0, INFINITY), 0.0),
        ('atan2', (-0.1, INFINITY), -0.0),
        ('atan2', (-INFINITY, 0.4), -math.pi / 2),
        ('atan2', (2.1, -INFINITY), math.pi),
        ('atan2', (0.0, -INFINITY), math.pi),
        ('atan2', (-0.1, -INFINITY), -math.pi),
        #
        ('fmod', (INFINITY, 1.0), ValueError),
        ('fmod', (1.0, INFINITY), 1.0),
        ('fmod', (1.0, -INFINITY), 1.0),
        ('fmod', (INFINITY, INFINITY), ValueError),
        #
        ('hypot', (-INFINITY, 1.0), positiveinf),
        ('hypot', (-2.3, -INFINITY), positiveinf),
        ]

    binary_math_functions = ['atan2', 'fmod', 'hypot', 'pow']

    NANCASES1 = [
        (name, (NAN,), isnan) for name in unary_math_functions]
    NANCASES2 = [
        (name, (NAN, 0.1), isnan) for name in binary_math_functions]
    NANCASES3 = [
        (name, (-0.2, NAN), isnan) for name in binary_math_functions]
    NANCASES4 = [
        (name, (NAN, -INFINITY), isnan) for name in binary_math_functions
                                        if name != 'hypot']
    NANCASES5 = [
        (name, (INFINITY, NAN), isnan) for name in binary_math_functions
                                       if name != 'hypot']
    NANCASES6 = [
        ('frexp', (NAN,), lambda x: isnan(x[0])),
        ('ldexp', (NAN, 2), isnan),
        ('hypot', (NAN, INFINITY), positiveinf),
        ('hypot', (NAN, -INFINITY), positiveinf),
        ('hypot', (INFINITY, NAN), positiveinf),
        ('hypot', (-INFINITY, NAN), positiveinf),
        ('modf', (NAN,), lambda x: (isnan(x[0]) and isnan(x[1]))),
        ]

    # The list of test cases.  Note that various tests import this,
    # notably in rpython/lltypesystem/module and in translator/c/test.
    TESTCASES = (REGCASES + IRREGCASES + OVFCASES + INFCASES + IRREGERRCASES
                 + NANCASES1 + NANCASES2 + NANCASES3 + NANCASES4 + NANCASES5
                 + NANCASES6)


class TestDirect(MathTests):
    pass

def get_tester(expected):
    if type(expected) is type(Exception):
        def tester(value):
            return False
    elif callable(expected):
        def tester(value):
            ok = expected(value)
            assert isinstance(ok, bool)
            return ok
    else:
        assert finite(expected), "badly written test"
        def tester(got):
            gotsign = expectedsign = 1
            if got < 0.0: gotsign = -gotsign
            if expected < 0.0: expectedsign = -expectedsign
            return finite(got) and (got == expected and
                                    gotsign == expectedsign)
    return tester

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

import sys
from pypy.translator.squeak.test.runtest import compile_function
from pypy.rpython.rarithmetic import r_uint
from pypy.rpython.annlowlevel import LowLevelAnnotatorPolicy
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.lltypesystem.lltype import Signed, Unsigned, Bool
from pypy.rpython.test.test_llinterp import interpret

def optest(testcase):
    llopname = testcase[0]
    RESTYPE = testcase[1] 
    args = testcase[2:]

    arg_signature = ", ".join(["v%s" % n for n in range(len(args))])
    exec """def lloptest(%s):
        return llop.%s(%s, %s)""" \
                % (arg_signature, llopname, RESTYPE._name,
                   arg_signature)

    annotation = [type(a) for a in args]
    sqfunc = compile_function(lloptest, annotation)
    expected_res = interpret(lloptest, args, policy=LowLevelAnnotatorPolicy())
    res = sqfunc(*args)
    assert res == str(expected_res).lower() # lowercasing for booleans

def adapt_tests(tests, type, RESTYPE, prefix):
    adapted = []
    for test in tests:
        llop = "%s_%s" % (prefix, test[0]) 
        RES = test[1]
        if RES == Signed:
            RES = RESTYPE
        args = [type(arg) for arg in test[2:]]
        adapted.append((llop, RES) + tuple(args))
    return adapted

general_tests = [
    # unary
    ("abs", Signed, 7),
    ("abs", Signed, -7),
    ("is_true", Bool, 8),
    ("is_true", Bool, 0),
    ("neg", Signed, 2),
    ("neg", Signed, -2),
    ("invert", Signed, 5),
    ("invert", Signed, -5),

    # binary
    ("add", Signed, 1, 2),
    ("sub", Signed, 1, 3),
    ("mul", Signed, 2, 3),
    ("div", Signed, 7, 3),
    ("floordiv", Signed, 7, 3),
    ("floordiv", Signed, -7, 3),
    ("mod", Signed, 9, 4),
    ("mod", Signed, 9, -4),
]

def test_intoperations():
    tests = adapt_tests(general_tests, int, Signed, "int") + [
        # binary wraparounds
        ("int_add", Signed, sys.maxint, 1),
        ("int_sub", Signed, -sys.maxint-1, 2),
        ("int_mul", Signed, sys.maxint/2, 3),
    ]
    for t in tests:
        yield optest, t

def test_uintoperations():
    tests = adapt_tests(general_tests, r_uint, Unsigned, "uint") + [
        # binary wraparounds
        ("uint_add", Unsigned, r_uint(2*sys.maxint), r_uint(2)),
        ("uint_sub", Unsigned, r_uint(1), r_uint(3)),
        ("uint_mul", Unsigned, r_uint(sys.maxint), r_uint(3)),
    ]
    for t in tests:
        yield optest, t


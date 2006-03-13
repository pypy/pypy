import sys
from pypy.translator.squeak.test.runtest import compile_function
from pypy.rpython.annlowlevel import LowLevelAnnotatorPolicy
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.lltypesystem.lltype import Signed, Bool
from pypy.rpython.test.test_llinterp import interpret

def optest(testcase):
    llopname = testcase[0]
    RESTYPE = testcase[1] 
    args = testcase[2:]

    llopfunc = getattr(llop, llopname)
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

def test_intoperations():
    tests = [
        # unary
        ("int_abs", Signed, 7),
        ("int_abs", Signed, -7),
        ("int_is_true", Bool, 8),
        ("int_is_true", Bool, 0),
        ("int_neg", Signed, 2),
        ("int_neg", Signed, -2),
        ("int_invert", Signed, 5),
        ("int_invert", Signed, -5),

        # binary
        ("int_add", Signed, 1, 2),
        ("int_sub", Signed, 1, 3),
        ("int_mul", Signed, 2, 3),
        ("int_div", Signed, 7, 3),
        ("int_floordiv", Signed, 7, 3),
        ("int_floordiv", Signed, -7, 3),

        # binary wraparounds
        ("int_add", Signed, sys.maxint, 1),
        ("int_sub", Signed, -sys.maxint-1, 2),
        ("int_mul", Signed, sys.maxint/2, 3),
    ]
    for t in tests:
        yield optest, t


from pypy.translator.squeak.test.runtest import compile_function
from pypy.rpython.annlowlevel import LowLevelAnnotatorPolicy
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.lltypesystem.lltype import Signed
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
    res = interpret(lloptest, args, policy=LowLevelAnnotatorPolicy())
    assert sqfunc(*args) == str(res)

def test_intoperations():
    tests = [
        # XXX Must handle overflows for all integer ops
        ("int_add", Signed, 1, 2),
        ("int_sub", Signed, 1, 3),
        ("int_mul", Signed, 2, 3),
        ("int_div", Signed, 7, 3),
        ("int_floordiv", Signed, 7, 3),
        ("int_floordiv", Signed, -7, 3),
        ("int_abs", Signed, 7),
        ("int_abs", Signed, -7),
    ]
    for t in tests:
        yield optest, t


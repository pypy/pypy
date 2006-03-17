import sys
from pypy.translator.squeak.test.runtest import compile_function
from pypy.rpython.rarithmetic import r_uint, r_longlong, r_ulonglong
from pypy.rpython.annlowlevel import LowLevelAnnotatorPolicy
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.lltypesystem.lltype import Signed, Unsigned, Bool, Char, UniChar
from pypy.rpython.lltypesystem.lltype import SignedLongLong, UnsignedLongLong
from pypy.rpython.test.test_llinterp import interpret

def optest(testcase):
    llopname = testcase[0]
    RESTYPE = testcase[1] 
    args = testcase[2:]

    arg_signature = ", ".join(["a%s" % n for n in range(len(args))])
    exec """def lloptest(%s):
        return llop.%s(%s, %s)""" \
                % (arg_signature, llopname, RESTYPE._name,
                   arg_signature)
    llfunctest(lloptest, args)

def llfunctest(llfunc, args):
    annotation = [type(a) for a in args]
    sqfunc = compile_function(llfunc, annotation)
    expected_res = interpret(llfunc, args, policy=LowLevelAnnotatorPolicy())
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
    ("floordiv", Signed, 7, 3), # XXX what about division by zero?
    ("floordiv", Signed, -7, 3),
    ("mod", Signed, 9, 4),
    ("mod", Signed, 9, -4),
    ("eq", Bool, 1, 1),
    ("eq", Bool, 1, 2),
    ("ne", Bool, 1, 1),
    ("ne", Bool, 1, 2),
    ("lt", Bool, 1, 2),
    ("le", Bool, 1, 2),
    ("gt", Bool, 1, 2),
    ("ge", Bool, 1, 2),
]

int_tests = general_tests + [
    ("and", Signed, 9, 5),
    ("and", Signed, 9, -5),
    ("or", Signed, 4, 5),
    ("or", Signed, 4, -5),
    ("lshift", Signed, 16, 2),
    ("rshift", Signed, 16, 2),
    ("xor", Signed, 9, 5),
    ("xor", Signed, 9, -5),
]

def test_intoperations():
    tests = adapt_tests(int_tests, int, Signed, "int") + [
        # binary wraparounds
        ("int_add", Signed, sys.maxint, 1),
        ("int_sub", Signed, -sys.maxint-1, 2),
        ("int_mul", Signed, sys.maxint/2, 3),
        ("int_lshift", Signed, sys.maxint, 1),
    ]
    for t in tests:
        yield optest, t

def test_uintoperations():
    tests = adapt_tests(int_tests, r_uint, Unsigned, "uint") + [
        # binary wraparounds
        ("uint_add", Unsigned, r_uint(2*sys.maxint), r_uint(2)),
        ("uint_sub", Unsigned, r_uint(1), r_uint(3)),
        ("uint_mul", Unsigned, r_uint(sys.maxint), r_uint(3)),
        ("uint_lshift", Unsigned, r_uint(2*sys.maxint), r_uint(1)),
    ]
    for t in tests:
        yield optest, t

def test_llongoperations():
    tests = adapt_tests(general_tests, r_longlong, SignedLongLong, "llong")
    for t in tests:
        yield optest, t

def test_ullongoperations():
    tests = adapt_tests(general_tests, r_ulonglong, UnsignedLongLong, "ullong") + [
        # binary wraparounds
        ("ullong_add", UnsignedLongLong,
                r_ulonglong(r_ulonglong.MASK), r_ulonglong(10)),
    ]
    for t in tests:
        yield optest, t

def test_booloperations():
    def bool_not(i):
        if i == 1:
            j = True
        else:
            j = False
        return llop.bool_not(Bool, j)
    llfunctest(bool_not, (1,))

def test_charoperations():
    for llopname in "eq", "ne", "lt", "gt", "le", "ge":
        exec """def lloptest(i1, i2):
            char1 = llop.cast_int_to_char(Char, i1)
            char2 = llop.cast_int_to_char(Char, i2)
            return llop.char_%s(Bool, char1, char2)""" % llopname
        yield llfunctest, lloptest, (1, 2)

def test_unicharoperations():
    for llopname in "eq", "ne":
        exec """def lloptest(i1, i2):
            char1 = llop.cast_int_to_unichar(UniChar, i1)
            char2 = llop.cast_int_to_unichar(UniChar, i2)
            return llop.unichar_%s(Bool, char1, char2)""" % llopname
        yield llfunctest, lloptest, (1, 2)


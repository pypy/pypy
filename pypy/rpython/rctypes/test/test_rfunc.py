import py
import sys
import pypy.rpython.rctypes.implementation
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.rpython.test.test_llinterp import interpret
from pypy.translator.c.test.test_genc import compile
from pypy import conftest
from pypy.rpython.rstr import string_repr
from pypy.rpython.lltypesystem import lltype

from ctypes import cdll
from ctypes import c_int, c_long, c_char_p, c_char, create_string_buffer

# __________ the standard C library __________

# LoadLibrary is deprecated in ctypes, this should be removed at some point
if "load" in dir(cdll):
    cdll_load = cdll.load
else:
    cdll_load = cdll.LoadLibrary

if sys.platform == 'win32':
    mylib = cdll_load('msvcrt.dll')
elif sys.platform == 'linux2':
    mylib = cdll_load('libc.so.6')
elif sys.platform == 'darwin':
    mylib = cdll.c
else:
    py.test.skip("don't know how to load the c lib for %s" % 
            sys.platform)
# ____________________________________________

labs = mylib.labs
labs.restype = c_long
labs.argtypes = [c_long]
def ll_labs(n):
    return abs(n)
labs.llinterp_friendly_version = ll_labs

atoi = mylib.atoi
atoi.restype = c_int
atoi.argtypes = [c_char_p]
def ll_atoi(p):
    "Very approximative ll implementation of atoi(), for testing"
    i = result = 0
    while '0' <= p[i] <= '9':
        result = result * 10 + ord(p[i]) - ord('0')
        i += 1
    return result
atoi.llinterp_friendly_version = ll_atoi


def test_labs(n=6):
    assert labs(n) == abs(n)
    assert labs(c_long(0)) == 0
    assert labs(-42) == 42
    return labs(n)

def test_atoi():
    assert atoi("") == 0
    assert atoi("42z7") == 42
    assert atoi("blah") == 0
    assert atoi("18238") == 18238
    A = c_char * 10
    assert atoi(A('\x00')) == 0
    assert atoi(A('4', '2', 'z', '7', '\x00')) == 42
    assert atoi(A('b', 'l', 'a', 'h', '\x00')) == 0
    assert atoi(A('1', '8', '2', '3', '8', '\x00')) == 18238

def test_ll_atoi():
    keepalive = []
    def str2subarray(string):
        llstring = string_repr.convert_const(string)
        keepalive.append(llstring)
        A = lltype.FixedSizeArray(lltype.Char, 1)
        return lltype.cast_subarray_pointer(lltype.Ptr(A), llstring.chars, 0)
    assert ll_atoi(str2subarray("")) == 0
    assert ll_atoi(str2subarray("42z7")) == 42
    assert ll_atoi(str2subarray("blah")) == 0
    assert ll_atoi(str2subarray("18238")) == 18238

class Test_annotation:
    def test_annotate_labs(self):
        a = RPythonAnnotator()
        s = a.build_types(test_labs, [int])
        assert s.knowntype == int
        if conftest.option.view:
            a.translator.view()

    def test_annotate_atoi(self):
        def fn(s):
            return atoi(s)
        a = RPythonAnnotator()
        s = a.build_types(fn, [str])
        assert s.knowntype == int
        if conftest.option.view:
            a.translator.view()

class Test_specialization:
    def test_specialize_labs(self):
        res = interpret(test_labs, [-11])
        assert res == 11

    def test_specialize_atoi(self):
        choices = ["", "42z7", "blah", "18238"]
        def fn(n):
            return atoi(choices[n])

        res = [interpret(fn, [i]) for i in range(4)]
        assert res == [0, 42, 0, 18238]

    def test_specialize_atoi_char_array(self):
        A = c_char * 10
        choices = [A('\x00'),
                   A('4', '2', 'z', '7', '\x00'),
                   A('b', 'l', 'a', 'h', '\x00'),
                   A('1', '8', '2', '3', '8', '\x00')]
        def fn(n):
            return atoi(choices[n])

        assert fn(3) == 18238
        res = [interpret(fn, [i]) for i in range(4)]
        assert res == [0, 42, 0, 18238]

    def test_specialize_atoi_stringbuf(self):
        def fn(n):
            buf = create_string_buffer(n)
            buf[0] = '4'
            buf[1] = '2'
            return atoi(buf)

        assert fn(11) == 42
        res = interpret(fn, [11])
        assert res == 42

class Test_compile:
    def test_compile_labs(self):
        fn = compile(test_labs, [int])
        res = fn(-11)
        assert res == 11

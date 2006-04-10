import py
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.rpython.rctypes.test.test_rctypes import mylib
from pypy.rpython.test.test_llinterp import interpret
from pypy.translator.c.test.test_genc import compile
from pypy import conftest
from pypy.rpython.rstr import string_repr

from ctypes import c_int, c_long, c_char_p


labs = mylib.labs
labs.restype = c_long
labs.argtypes = [c_long]
def ll_labs(n):
    return abs(n)
labs.llinterp_friendly_version = ll_labs

atoi = mylib.atoi
atoi.restype = c_int
atoi.argtypes = [c_char_p]
def ll_atoi(s):
    "Very approximative ll implementation of atoi(), for testing"
    i = result = 0
    while i < len(s.chars):
        if '0' <= s.chars[i] <= '9':
            result = result * 10 + ord(s.chars[i]) - ord('0')
        else:
            break
        i += 1
    return result
atoi.llinterp_friendly_version = ll_atoi


def test_labs(n=6):
    assert labs(n) == abs(n)
    assert labs(c_long(0)) == 0
    assert labs(-42) == 42
    return labs(n)

def test_ll_atoi():
    assert ll_atoi(string_repr.convert_const("")) == 0
    assert ll_atoi(string_repr.convert_const("42z7")) == 42
    assert ll_atoi(string_repr.convert_const("blah")) == 0
    assert ll_atoi(string_repr.convert_const("18238")) == 18238

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
        py.test.skip("in-progress")
        choices = ["", "42z7", "blah", "18238"]
        def fn(n):
            return atoi(choices[n])

        res = [interpret(fn, [i]) for i in range(4)]
        assert res == [0, 42, 0, 18238]

class Test_compile:
    def test_compile_labs(self):
        fn = compile(test_labs, [int])
        res = fn(-11)
        assert res == 11

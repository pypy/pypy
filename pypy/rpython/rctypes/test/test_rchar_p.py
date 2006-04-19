"""
Test the c_char_p implementation.
"""

import py.test
import pypy.rpython.rctypes.implementation
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.translator.translator import TranslationContext
from pypy.translator.c.test.test_genc import compile
from pypy.annotation.model import SomeCTypesObject, SomeObject
from pypy import conftest
import sys
from pypy.rpython.test.test_llinterp import interpret

from ctypes import c_char_p, pointer, Structure

class Test_annotation:
    def test_annotate_c_char_p(self):
        def func():
            p = c_char_p("hello")
            return p.value

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(func, [])
        assert s.knowntype == str
        if conftest.option.view:
            t.view()

    def test_annotate_prebuilt(self):
        p = c_char_p("hello")
        def func():
            return p.value

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(func, [])
        assert s.knowntype == str
        if conftest.option.view:
            t.view()

    def test_annotate_return(self):
        class S(Structure):
            _fields_ = [('string', c_char_p)]
        def func():
            s = S()
            s.string = "hello"
            return s.string

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(func, [])
        assert s.knowntype == str
        if conftest.option.view:
            t.view()

class Test_specialization:
    def test_specialize_c_char_p(self):
        def func():
            p = c_char_p("hello")
            return p.value

        res = interpret(func, [])
        assert ''.join(res.chars) == "hello"

    def test_specialize_prebuilt(self):
        p = c_char_p("hello")
        def func():
            return p.value

        res = interpret(func, [])
        assert ''.join(res.chars) == "hello"

    def test_zero_terminates(self):
        def func():
            p = c_char_p('world')
            p.value = "hello\x00world"
            return p.value

        res = interpret(func, [])
        assert ''.join(res.chars) == "hello"

    def test_pointer_access(self):
        def func():
            q = c_char_p('ka')
            p = c_char_p('world')
            pp = pointer(p)
            pp[0] = q.value
            return p.value

        assert func() == 'ka'
        res = interpret(func, [])
        assert ''.join(res.chars) == 'ka'

    def test_specialize_return(self):
        class S(Structure):
            _fields_ = [('string', c_char_p)]
        def func():
            s = S()
            s.string = "hello"
            return s.string

        assert func() == "hello"
        res = interpret(func, [])
        assert ''.join(res.chars) == "hello"


class Test_compilation:
    def test_compile_c_char_p(self):
        def func():
            p = c_char_p("hello")
            return p.value

        fn = compile(func, [])
        res = fn()
        assert res == "hello"

    def test_compile_prebuilt(self):
        p = c_char_p("hello")
        def func():
            return p.value

        fn = compile(func, [])
        res = fn()
        assert res == "hello"

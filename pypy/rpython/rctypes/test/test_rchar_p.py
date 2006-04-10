"""
Test the rctypes implementation.
"""

import py.test
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.translator.translator import TranslationContext
from pypy.translator.c.test.test_genc import compile
from pypy.annotation.model import SomeCTypesObject, SomeObject
from pypy import conftest
import sys
from pypy.rpython.test.test_llinterp import interpret

try:
    import ctypes
except ImportError:
    py.test.skip("this test needs ctypes installed")

from ctypes import c_char_p

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

class Test_specialization:
    def test_specialize_c_char_p(self):
        def func():
            p = c_char_p("hello")
            return p.value

        res = interpret(func, [])
        assert ''.join(res.chars) == "hello"

class Test_compilation:
    pass

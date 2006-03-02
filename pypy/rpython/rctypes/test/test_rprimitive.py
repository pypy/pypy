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

from ctypes import c_char, c_byte, c_ubyte, c_short, c_ushort, c_int, c_uint
from ctypes import c_long, c_ulong, c_longlong, c_ulonglong, c_float
from ctypes import c_double, c_char_p

class Test_annotation:
    def test_simple(self):
        res = c_int(42)
        assert res.value == 42 

    def test_annotate_c_int(self):
        def func():
            res = c_int(42)

            return res.value

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(func, [])

        assert s.knowntype == int

        if conftest.option.view:
            t.view()

    def test_annotate_c_int_2(self):
        res = c_int(42)

        def func():
            return res.value

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(func, [])

        assert s.knowntype == int

        if conftest.option.view:
            t.view()

class Test_specialization:
    def test_specialize_c_int(self):
        def create_c_int():
            return c_int(42)
        res = interpret(create_c_int, [])
        c_data = res.c_data
        assert c_data.value == 42

    def test_specialize_c_int_default_value(self):
        def create_c_int():
            return c_int()
        res = interpret(create_c_int, [])
        c_data = res.c_data
        assert c_data.value == 0

    def test_specialize_c_int_access_value(self):
        def create_c_int():
            return c_int(42).value
        res = interpret(create_c_int, [])
        assert res == 42

class Test_compilation:
    def test_compile_c_int(self):
        def create_c_int():
            return c_int(42).value
        fn = compile(create_c_int, [])
        assert fn() == 42

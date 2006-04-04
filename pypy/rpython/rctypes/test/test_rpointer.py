"""
Test the rctypes pointer implementation
"""

import py.test
from pypy.translator.translator import TranslationContext
from pypy import conftest
from pypy.rpython.test.test_llinterp import interpret

from ctypes import c_int, c_float, POINTER

import pypy.rpython.rctypes.implementation

class Test_annotation:
    def test_simple(self):
        res = c_int(42)
        ptrres = POINTER(c_int)(res)
        assert res.value == ptrres.contents.value

    def test_annotate_c_int_ptr(self):
        ptrtype = POINTER(c_int)
        def func():
            res = c_int(42)
            ptrres  = ptrtype(res)
            return ptrres.contents.value
        
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(func, [])

        if conftest.option.view:
            t.view()

        assert s.knowntype == int

    def test_annotate_c_float_ptr(self):
        ptrtype = POINTER(c_float)
        def func():
            res = c_float(4.2)
            ptrres  = ptrtype(res)
            return ptrres.contents.value
        
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(func, [])

        if conftest.option.view:
            t.view()

        assert s.knowntype == float

class Test_specialization:
    def test_specialize_c_int_ptr(self):
        ptrtype = POINTER(c_int)
        def func():
            res = c_int(42)
            ptrres = ptrtype(res)
            return ptrres.contents.value

        res = interpret(func, [])
        assert res == 42

    def test_specialize_mutate_via_pointer(self):
        ptrtype = POINTER(c_int)
        def func():
            res = c_int(6)
            p1 = ptrtype(res)
            p2 = ptrtype(p1.contents)
            p2.contents.value *= 7
            return res.value

        res = interpret(func, [])
        assert res == 42

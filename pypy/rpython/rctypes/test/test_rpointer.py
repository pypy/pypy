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
        def func():
            res = c_int(42)
            ptrtype  = POINTER(c_int)
            ptrres  = ptrtype(res)
            return ptrres.contents.value
        
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(func, [])

        if conftest.option.view:
            t.view()

        assert s.knowntype == int

    def test_annotate_c_float_ptr(self):
        def func():
            res = c_float(4.2)
            ptrtype  = POINTER(c_float)
            ptrres  = ptrtype(res)
            return ptrres.contents.value
        
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(func, [])

        if conftest.option.view:
            t.view()

        assert s.knowntype == float

class Test_specialization:
    def x_test_specialize_c_int_ptr(self):
        def func():
            res = c_int(42)
            ptrtype  = POINTER(c_int)
            ptrres  = ptrtype(res)

            return ptrres.contents.value

        res = interpret(func, [])

        assert res == 42

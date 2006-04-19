"""
Test the special py_object support.
"""

import py
import pypy.rpython.rctypes.implementation
from pypy.annotation import model as annmodel
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.translator.translator import TranslationContext
from pypy import conftest
from pypy.translator.c.test.test_genc import compile
import sys
from pypy.rpython.test.test_llinterp import interpret
from pypy.rpython.lltypesystem import lltype

from ctypes import py_object


class Test_annotation:
    def test_annotate_wrapping(self):
        def wrap(x):
            return py_object(x)

        a = RPythonAnnotator()
        s = a.build_types(wrap, [int])
        assert s.knowntype == py_object
        if conftest.option.view:
            a.translator.view()

        a = RPythonAnnotator()
        s = a.build_types(wrap, [str])
        assert s.knowntype == py_object
        if conftest.option.view:
            a.translator.view()

    def test_annotate_prebuilt(self):
        five = py_object(5)
        hello = py_object("hello")

        def fn(i):
            return [five, hello][i]

        a = RPythonAnnotator()
        s = a.build_types(fn, [int])
        assert s.knowntype == py_object
        if conftest.option.view:
            a.translator.view()

class Test_specialization:
    def test_specialize_wrapping(self):
        def wrap(x):
            return py_object(x)

        res = interpret(wrap, [9])
        assert lltype.typeOf(res.c_data[0]) == lltype.Ptr(lltype.PyObject)
        assert res.c_data[0]._obj.value == 9

    def test_specialize_ass_value(self):
        # reading .value is not allowed, as it can't be annotated!
        def func(x):
            o = py_object()
            o.value = x

        interpret(func, [9])
        interpret(func, [9.2])

    def test_specialize_prebuilt(self):
        five = py_object(5)
        hello = py_object("hello")

        def fn(i):
            return [five, hello][i]

        res = interpret(fn, [0])
        assert res.c_data[0]._obj.value == 5
        res = interpret(fn, [1])
        assert res.c_data[0]._obj.value == "hello"

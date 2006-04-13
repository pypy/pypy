"""
Test the rctypes implementation.
"""

import py.test
import pypy.rpython.rctypes.implementation
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.translator.translator import TranslationContext
from pypy import conftest
from pypy.translator.c.test.test_genc import compile
import sys
from pypy.rpython.test.test_llinterp import interpret

try:
    import ctypes
except ImportError:
    py.test.skip("this test needs ctypes installed")

from ctypes import c_int, c_short, Structure, POINTER, pointer

class tagpoint(Structure):
    _fields_ = [("x", c_int),
                ("y", c_int)]

class Test_annotation:
    def test_annotate_struct(self):
        def create_struct():
            return tagpoint()

        a = RPythonAnnotator()
        s = a.build_types(create_struct, [])
        assert s.knowntype == tagpoint

        if conftest.option.view:
            a.translator.view()

    def test_annotate_struct_access(self):
        def access_struct(n):
            my_point = tagpoint()
            my_point.x = c_int(1)
            my_point.y = 2
            my_point.x += n

            return my_point.x

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(access_struct, [int])
        assert s.knowntype == int

        if conftest.option.view:
            t.view()

    def test_annotate_prebuilt(self):
        my_struct_2 = tagpoint(5, 7)
        my_struct_3 = tagpoint(x=6, y=11)
        def func(i):
            if i == 2:
                struct = my_struct_2
            else:
                struct = my_struct_3
            return struct.y

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(func, [int])
        if conftest.option.view:
            a.translator.view()
        assert s.knowntype == int

class Test_specialization:
    def test_specialize_struct(self):
        def create_struct():
            return tagpoint()

        res = interpret(create_struct, [])
        c_data = res.c_data
        assert c_data.x == 0
        assert c_data.y == 0

    def test_specialize_struct_access(self):
        def access_struct(n):
            my_struct = tagpoint()
            my_struct.x = c_int(1)
            my_struct.y = 2
            my_struct.x += n

            return my_struct.x * my_struct.y

        res = interpret(access_struct, [44])
        assert res == 90

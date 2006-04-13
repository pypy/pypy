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

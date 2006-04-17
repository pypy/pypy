"""
Test the rctypes implementation.
"""

import py.test
import pypy.rpython.rctypes.implementation
from pypy.annotation import model as annmodel
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

from ctypes import create_string_buffer
from pypy.rpython.rctypes.astringbuf import StringBufferType


class Test_annotation:
    def test_annotate_create(self):
        def func(n):
            return create_string_buffer(n)

        a = RPythonAnnotator()
        s = a.build_types(func, [int])
        assert s.knowntype == StringBufferType

        if conftest.option.view:
            a.translator.view()

    def test_annotate_access(self):
        def func(n):
            buf = create_string_buffer(n)
            buf[0] = 'x'
            buf[1] = 'y'
            return buf[0]

        a = RPythonAnnotator()
        s = a.build_types(func, [int])
        assert s == annmodel.SomeChar()

        if conftest.option.view:
            a.translator.view()

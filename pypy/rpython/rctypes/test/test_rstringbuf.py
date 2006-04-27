"""
Test the create_string_buffer() implementation.
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

from ctypes import create_string_buffer, sizeof, c_int
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

    def test_annotate_len(self):
        def func(n):
            buf = create_string_buffer(n)
            return len(buf)

        a = RPythonAnnotator()
        s = a.build_types(func, [int])
        assert s.knowntype == int

        if conftest.option.view:
            a.translator.view()

class Test_specialization:
    def test_specialize_create(self):
        def func(n):
            return create_string_buffer(n)

        res = interpret(func, [17])
        c_data = res.c_data
        assert c_data[0] == '\x00'
        assert c_data[16] == '\x00'
        assert len(c_data) == 17
        py.test.raises(IndexError, "c_data[17]")

    def test_specialize_access(self):
        def func(n):
            buf = create_string_buffer(n)
            buf[0] = 'x'
            buf[1] = 'y'
            return buf[0]

        res = interpret(func, [17])
        assert res == 'x'

    def test_specialize_len(self):
        def func(n):
            buf = create_string_buffer(n)
            return len(buf)

        res = interpret(func, [17])
        assert res == 17
        res = interpret(func, [0])
        assert res == 0

    def test_specialize_value(self):
        def func(n):
            buf = create_string_buffer(n)
            buf[0] = 'x'
            buf[1] = 'y'
            return buf.value

        res = interpret(func, [12])
        assert ''.join(res.chars) == "xy"

    def test_specialize_sizeof(self):
        def func(n):
            buf = create_string_buffer(n)
            return sizeof(buf)
        res = interpret(func, [117])
        assert res == 117


class Test_compilation:
    def test_compile_const_sizeof(self):
        A = c_int * 42
        def func():
            x = c_int()
            a = A()
            return sizeof(x), sizeof(a), sizeof(c_int), sizeof(A)
        fn = compile(func, [])
        res = fn()
        assert res[0] == sizeof(c_int)
        assert res[1] == sizeof(c_int) * 42
        assert res[2] == sizeof(c_int)
        assert res[3] == sizeof(c_int) * 42

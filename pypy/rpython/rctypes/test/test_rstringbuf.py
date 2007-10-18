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

from ctypes import create_string_buffer, cast, POINTER, c_void_p, c_char
from ctypes import c_char_p, c_long, pointer, sizeof, c_int
from pypy.rpython.rctypes.astringbuf import StringBufferType
from pypy.rlib.rarithmetic import r_uint
from pypy.rlib.objectmodel import keepalive_until_here


class Test_annotation:
    def test_annotate_create(self):
        def func(n):
            return create_string_buffer(n)

        a = RPythonAnnotator()
        s = a.build_types(func, [int])
        assert s.knowntype == StringBufferType

        if conftest.option.view:
            a.translator.view()

        a = RPythonAnnotator()
        s = a.build_types(func, [r_uint])
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

    def test_annotate_slice(self):
        def func(n):
            buf = create_string_buffer(n)
            buf[0] = 'x'
            buf[1] = 'y'
            return buf[:2]

        a = RPythonAnnotator()
        s = a.build_types(func, [int])
        assert s == annmodel.SomeString()

    def test_annotate_cast_to_ptr(self):
        charp = POINTER(c_char)
        def func(n):
            buf = create_string_buffer(n)
            buf[0] = 'x'
            buf[1] = 'y'
            buf[2] = 'z'
            cp = cast(buf, charp)
            vp = cast(buf, c_void_p)
            return  cp[0] + cast(vp, charp)[2]
        
        a = RPythonAnnotator()
        s = a.build_types(func, [int])
        assert s == annmodel.SomeString()

            
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

        res = interpret(func, [r_uint(17)])
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

    def test_specialize_raw(self):
        def func(n):
            buf = create_string_buffer(n)
            buf[0] = 'x'
            buf[1] = '\x00'
            buf[2] = 'y'
            return buf.raw

        res = interpret(func, [3])
        assert ''.join(res.chars) == "x\x00y"

    def test_specialize_setvalue(self):
        def func(n):
            buf = create_string_buffer(n)
            buf.value = 'abcde'
            assert buf.value == 'abcde'
            buf.value = 'x'
            assert buf.value == 'x'
            buf.raw = 'y'
            assert buf.value == 'y'
            return ord(buf[2])

        res = interpret(func, [12])
        assert res == ord('c')    # not overridden by buf.value='x'

    def test_specialize_slice(self):
        def func(n):
            buf = create_string_buffer(n)
            buf[0] = 'x'
            buf[1] = 'y'
            buf[2] = 'z'
            return buf[:2] + '_' + buf[1:3] + '_' + buf[9:]

        res = interpret(func, [12])
        assert ''.join(res.chars) == "xy_yz_\0\0\0"

    def test_specialize_cast_to_ptr(self):
        charp = POINTER(c_char)
        def func(n):
            buf = create_string_buffer(n)
            buf[0] = 'x'
            buf[1] = 'y'
            buf[2] = 'z'
            cp = cast(buf, charp)
            vp = cast(buf, c_void_p)
            return  cp[0] + '_' + cast(vp, charp)[2]
        
        res = interpret(func, [12])
        assert ''.join(res.chars) == 'x_z'

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

    def test_compile_cast_to_ptr(self):
        charp = POINTER(c_char)
        def func(n):
            c_n = c_long(n)
            c_n_ptr = cast(pointer(c_n), POINTER(c_char))
            buf = create_string_buffer(sizeof(c_long))
            for i in range(sizeof(c_long)):
                buf[i] = c_n_ptr[i]
            c_long_ptr = cast(buf, POINTER(c_long))
            res = c_long_ptr.contents.value
            keepalive_until_here(buf)
            return res
        fn = compile(func, [int])
        res = fn(0x12345678)
        assert res == 0x12345678

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

from ctypes import c_int, c_short, Structure, POINTER, pointer, c_char_p

class tagpoint(Structure):
    _fields_ = [("x", c_int),
                ("y", c_int)]

def maketest():
    class S1(Structure): _fields_ = [('x', c_int)]
    class S2(Structure): _fields_ = [('x', POINTER(c_int))]
    class S3(Structure): _fields_ = [('x', S1)]
    class S4(Structure): _fields_ = [('x', POINTER(S1))]
    class S5(Structure): _fields_ = [('x', c_char_p)]
    def func():
        s1 = S1(); s1.x = 500
        s2 = S2(); s2.x = pointer(c_int(200))
        s3 = S3(); s3.x.x = 30
        s4 = S4(); s4.x = pointer(s1)
        s5 = S5(); s5.x = "hello"
        res = s1.x + s2.x.contents.value + s3.x.x + s4.x.contents.x
        res *= ord(s5.x[4])
        return res
    return func, 1230 * ord('o')


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

    def test_annotate_variants(self):
        func, expected = maketest()
        assert func() == expected
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(func, [])
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

    def test_specialize_prebuilt(self):
        my_struct_2 = tagpoint(5, 7)
        my_struct_3 = tagpoint(x=6, y=11)
        def func(i):
            if i == 2:
                struct = my_struct_2
            else:
                struct = my_struct_3
            return struct.y

        res = interpret(func, [2])
        assert res == 7
        res = interpret(func, [3])
        assert res == 11

    def test_specialize_variants(self):
        func, expected = maketest()
        res = interpret(func, [])
        assert res == expected

    def test_struct_of_pointers(self):
        class S(Structure):
            _fields_ = [('x', c_int)]
        class T(Structure):
            _fields_ = [('p', POINTER(S))]
        def func():
            t1 = T()
            t2 = T()
            s = S()
            s.x = 11
            t1.p = pointer(s)
            t2.p.contents = s
            return t1.p.contents.x * t2.p.contents.x
        res = interpret(func, [])
        assert res == 121

class Test_compilation:
    def test_compile_struct_access(self):
        def access_struct(n):
            my_struct = tagpoint()
            my_struct.x = c_int(1)
            my_struct.y = 2
            my_struct.x += n

            return my_struct.x * my_struct.y

        fn = compile(access_struct, [int])
        assert fn(44) == 90

    def test_compile_prebuilt(self):
        my_struct_2 = tagpoint(5, 7)
        my_struct_3 = tagpoint(x=6, y=11)
        def func(i):
            if i == 2:
                struct = my_struct_2
            else:
                struct = my_struct_3
            return struct.y

        fn = compile(func, [int])
        assert fn(2) == 7
        assert fn(3) == 11

    def test_compile_variants(self):
        func, expected = maketest()
        fn = compile(func, [])
        assert fn() == expected

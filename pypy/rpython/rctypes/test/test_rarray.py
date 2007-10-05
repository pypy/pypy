"""
Test the array implementation.
"""

import py
import pypy.rpython.rctypes.implementation
from pypy.annotation import model as annmodel
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.translator.translator import TranslationContext
from pypy import conftest
import sys
from pypy.rpython.test.test_llinterp import interpret

from ctypes import c_int, c_short, c_char_p, c_char, c_ubyte, pointer, cast
from ctypes import ARRAY, POINTER, Structure

c_int_10 = ARRAY(c_int,10)

def maketest():
    A1 = c_int * 10
    A2 = POINTER(c_int) * 10
    A3 = A1 * 10
    A4 = POINTER(A1) * 10
    A5 = c_char_p * 10
    def func():
        a1 = A1(); a1[4] = 1000
        a2 = A2(); a2[5] = pointer(c_int(200))
        a3 = A3(); a3[2][9] = 30
        a4 = A4(); a4[3] = pointer(a1); a1[1] = 4
        a5 = A5(); a5[7] = "hello"
        res = a1[4] + a2[5].contents.value + a3[2][9] + a4[3].contents[1]
        res *= ord(a5[7][1])
        return res
    return func, 1234 * ord('e')

def test_base():
    func, expected = maketest()
    assert func() == expected


class Test_annotation:
    def test_annotate_array(self):
        def create_array():
            return c_int_10()

        a = RPythonAnnotator()
        s = a.build_types(create_array, [])
        assert s.knowntype == c_int_10

        if conftest.option.view:
            a.translator.view()

    def test_annotate_array_access(self):
        def access_array(n):
            my_array = c_int_10()
            my_array[0] = c_int(1)
            my_array[1] = 2
            my_array[2] = n

            return my_array[0]

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(access_array, [int])
        assert s.knowntype == int

        if conftest.option.view:
            t.view()

##    def test_annotate_array_slice_access(self):
##        def slice_access():
##            my_array = c_int_10()
##            #f#my_array[0:7] = c_int(1) * 7
##            my_array[0:5] = range(5)

##            return my_array[0:5]

##        t = TranslationContext()
##        a = t.buildannotator()
##        s = a.build_types(slice_access, [])
##        #d#t.view()
##        #d#print "v90:", s, type(s)
##        assert s.knowntype == list
##        s.listdef.listitem.s_value.knowntype == int

    def test_annotate_array_access_variable(self):
        def access_with_variable():
            my_array = c_int_10()
            my_array[2] = 2
            sum = 0
            for idx in range(10):
                sum += my_array[idx]

            return sum

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(access_with_variable, [])
        assert s.knowntype == int
        #t#t.view()

##    def test_annotate_array_access_index_error_on_positive_index(self):
##        def access_with_invalid_positive_index():
##            my_array = c_int_10()
##            return my_array[10]

##        t = TranslationContext()
##        a = t.buildannotator()
        
##        py.test.raises(IndexError, "s = a.build_types(access_with_invalid_positive_index,[])")

##    def test_annotate_array_access_index_error_on_negative_index(self):
##        def access_with_invalid_negative_index():
##            my_array = c_int_10()
##            return my_array[-11]

##        t = TranslationContext()
##        a = t.buildannotator()
        
##        py.test.raises(IndexError, "s = a.build_types(access_with_invalid_negative_index,[])")

    def test_annotate_prebuilt(self):
        my_array_2 = (c_short*10)(0, 1, 4, 9, 16, 25, 36, 49, 64, 81)
        my_array_3 = (c_short*10)(0, 1, 8, 27, 64, 125, 216, 343, 512, 729)
        def func(i, n):
            if i == 2:
                array = my_array_2
            else:
                array = my_array_3
            return array[n]

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(func, [int, int])
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

    def test_annotate_char_array_value(self):
        A = c_char * 3
        def func():
            a = A()
            a[0] = 'x'
            a[1] = 'y'
            return a.value
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(func, [])
        if conftest.option.view:
            a.translator.view()
        assert s == annmodel.SomeString()

    def test_annotate_char_array_slice(self):
        A = c_char * 3
        def func():
            a = A()
            a[0] = 'x'
            a[1] = 'y'
            a[2] = 'z'
            return a[0:2]
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(func, [])
        if conftest.option.view:
            a.translator.view()
        assert s == annmodel.SomeString()

    def test_annotate_varsize_array(self):
        def func(n):
            a = (c_int * n)()
            a[n//2] = 12
            return a[n//3]
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(func, [int])
        if conftest.option.view:
            a.translator.view()
        assert s.knowntype == int

class Test_specialization:
    def test_specialize_array(self):
        def create_array():
            return c_int_10()

        res = interpret(create_array, [])
        c_data = res.c_data
        assert c_data[0] == 0
        assert c_data[9] == 0
        py.test.raises(IndexError, "c_data[10]")
        assert len(c_data) == 10

    def test_specialize_array_access(self):
        def access_array(n):
            my_array = c_int_10()
            my_array[0] = 1
            my_array[1] = c_int(1)
            my_array[2] = n

            return my_array[0]

        res = interpret(access_array, [44])
        assert res == 1

    def test_specialize_prebuilt(self):
        my_array_2 = (c_short*10)(0, 1, 4, 9, 16, 25, 36, 49, 64, 81)
        my_array_3 = (c_short*10)(0, 1, 8, 27, 64, 125, 216, 343, 512, 729)
        def func(i, n):
            if i == 2:
                array = my_array_2
            else:
                array = my_array_3
            return array[n]

        res = interpret(func, [2, 6])
        assert res == 36
        res = interpret(func, [3, 7])
        assert res == 343

    def test_specialize_variants(self):
        func, expected = maketest()
        res = interpret(func, [])
        assert res == expected

    def test_specialize_char_array_value(self):
        A = c_char * 3
        def func():
            a = A()
            a[0] = 'x'
            a[1] = 'y'
            return a.value
        res = interpret(func, [])
        assert ''.join(res.chars) == "xy"

    def test_specialize_char_array_slice(self):
        A = c_char * 3
        def func(n):
            a = A()
            a[0] = 'x'
            a[1] = 'y'
            a[2] = 'z'
            assert n >= 0
            return a[0:n]
        res = interpret(func, [1])
        assert ''.join(res.chars) == "x"
        res = interpret(func, [3])
        assert ''.join(res.chars) == "xyz"

    def test_automatic_cast_array_to_pointer(self):
        A = c_int * 10
        class S(Structure):
            _fields_ = [('p', POINTER(c_int))]
        def func():
            a = A()
            s = S()
            s.p = a
            s.p.contents.value = 42
            return a[0]
        res = interpret(func, [])
        assert res == 42

    def test_array_of_pointers(self):
        class S(Structure):
            _fields_ = [('x', c_int)]
        A = POINTER(S) * 10
        def func():
            a = A()
            s = S()
            s.x = 11
            a[2].contents = s
            a[3] = pointer(s)
            return a[2].contents.x * a[3].contents.x
        res = interpret(func, [])
        assert res == 121

    def test_specialize_keepalive(self):
        class S(Structure):
            _fields_ = [('x', c_int)]
        A = POINTER(S) * 10
        def func():
            a = A()
            for i in range(10):
                s = S()
                s.x = i*i
                a[i] = pointer(s)
            for i in range(10):
                assert a[i].contents.x == i*i
        func()
        interpret(func, [])

    def test_specialize_constructor_args(self):
        A = c_int * 5
        def func(x, y):
            return A(x, y)
        res = interpret(func, [123, 456])
        assert res.c_data[0] == 123
        assert res.c_data[1] == 456
        assert res.c_data[2] == 0
        assert res.c_data[3] == 0
        assert res.c_data[4] == 0

    def test_specialize_constructor_stararg(self):
        A = c_int * 5
        def func(x, y):
            args = (x, y)
            return A(*args)
        res = interpret(func, [123, 456])
        assert res.c_data[0] == 123
        assert res.c_data[1] == 456
        assert res.c_data[2] == 0
        assert res.c_data[3] == 0
        assert res.c_data[4] == 0

    def test_specialize_varsize_array_constructor(self):
        def func(n):
            return (c_int * n)()
        res = interpret(func, [12])
        py.test.raises(TypeError, "len(res.c_data)")    # nolength hint
        assert res.c_data[0] == 0
        assert res.c_data[11] == 0
        py.test.raises(IndexError, "res.c_data[12]")

    def test_specialize_varsize_array(self):
        def func(n):
            a = (c_int * n)(5)
            for i in range(1, n):
                a[i] = i
            res = 0
            for i in range(n):
                res += a[i]
            return res
        res = interpret(func, [10])
        assert res == 50

    def test_specialize_array_of_struct(self):
        py.test.skip("known to fail, sorry :-(")
        class T(Structure):
            _fields_ = [('x', c_int)]
        class S(Structure):
            _fields_ = [('p', POINTER(T))]
        A = S * 10
        def func():
            a = A()
            for i in range(10):
                t = T()
                t.x = i*i
                a[i].p = pointer(t)
            for i in range(10):
                assert a[i].p.contents.x == i*i
        func()
        interpret(func, [])

class Test_compilation:
    def setup_class(self):
        from pypy.translator.c.test.test_genc import compile
        self.compile = lambda s, x, y : compile(x, y)

    def test_compile_array_access(self):
        def access_array():
            my_array = c_int_10()
            my_array[0] = 1
            my_array[1] = c_int(2)

            return my_array[1]

        fn = self.compile(access_array, [])
        
        assert fn() == 2

    def test_compile_prebuilt(self):
        my_array_2 = (c_short*10)(0, 1, 4, 9, 16, 25, 36, 49, 64, 81)
        my_array_3 = (c_short*10)(0, 1, 8, 27, 64, 125, 216, 343, 512, 729)
        def func(i, n):
            if i == 2:
                array = my_array_2
            else:
                array = my_array_3
            return array[n]

        fn = self.compile(func, [int, int])
        assert fn(2, 7) == 49
        assert fn(3, 6) == 216

    def test_compile_variants(self):
        func, expected = maketest()
        fn = self.compile(func, [])
        assert fn() == expected

    def test_compile_char_array_value(self):
        A = c_char * 3
        def func():
            a = A()
            a[0] = 'x'
            a[1] = 'y'
            return a.value
        fn = self.compile(func, [])
        assert fn() == "xy"

    def test_compile_varsize_cast(self):
        # this cannot work on top of lltype, but only in unsafe C
        import struct
        N = struct.calcsize("i")
        BYTES = list(enumerate(struct.pack("i", 12345678)))
        def func(n):
            x = c_int()
            arraytype = c_ubyte * n     # runtime length
            p = cast(pointer(x), POINTER(arraytype))
            for i, c in BYTES:
                p.contents[i] = ord(c)
            return x.value
        fn = self.compile(func, [int])
        res = fn(N)
        assert res == 12345678

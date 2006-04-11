"""
Test the rctypes implementation.
"""

import py.test
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

from ctypes import c_int, c_short, ARRAY, POINTER, pointer

c_int_10 = ARRAY(c_int,10)

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

class Test_specialization:
    def test_specialize_array(self):
        def create_array():
            return c_int_10()

        res = interpret(create_array, [])
        c_data = res.c_data
        assert c_data[0][0] == 0
        assert c_data[9][0] == 0
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

class Test_compilation:
    def test_compile_array_access(self):
        def access_array():
            my_array = c_int_10()
            my_array[0] = 1
            my_array[1] = c_int(2)

            return my_array[1]

        fn = compile(access_array, [])
        
        assert fn() == 2

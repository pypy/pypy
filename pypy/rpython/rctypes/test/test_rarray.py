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

from ctypes import c_int, ARRAY, POINTER, pointer

c_int_10 = ARRAY(c_int,10)

#py.test.skip("Reworking primitive types")

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
        def access_array():
            my_array = c_int_10()
            my_array[0] = c_int(1)
            my_array[1] = 2

            return my_array[0]

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(access_array, [])
        assert s.knowntype == int

        if conftest.option.view:
            t.view()

    def x_test_annotate_array_slice_access(self):
        def slice_access():
            my_array = c_int_10()
            #f#my_array[0:7] = c_int(1) * 7
            my_array[0:5] = range(5)

            return my_array[0:5]

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(slice_access, [])
        #d#t.view()
        #d#print "v90:", s, type(s)
        assert s.knowntype == list
        s.listdef.listitem.s_value.knowntype == int

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

    def test_annotate_array_access_index_error_on_positive_index(self):
        def access_with_invalid_positive_index():
            my_array = c_int_10()
            return my_array[10]

        t = TranslationContext()
        a = t.buildannotator()
        
        py.test.raises(IndexError, "s = a.build_types(access_with_invalid_positive_index,[])")

    def test_annotate_array_access_index_error_on_negative_index(self):
        def access_with_invalid_negative_index():
            my_array = c_int_10()
            return my_array[-11]

        t = TranslationContext()
        a = t.buildannotator()
        
        py.test.raises(IndexError, "s = a.build_types(access_with_invalid_negative_index,[])")

class Test_specialization:
    def test_specialize_array(self):
        def create_array():
            return c_int_10()

        res = interpret(create_array, [])
        c_data = res.c_data
        assert c_data[0].value == 0
        assert c_data[9].value == 0
        py.test.raises(IndexError, "c_data[10]")
        assert len(c_data) == 10

    def test_specialize_array_access(self):
        def access_array():
            my_array = c_int_10()
            my_array[0] = 1
            my_array[1] = c_int(1)

            return my_array[0]

        res = interpret(access_array, [])
        assert res == 1

class Test_compilation:
    def test_compile_array_access(self):
        def access_array():
            my_array = c_int_10()
            my_array[0] = 1
            my_array[1] = c_int(2)

            return my_array[1]

        fn = compile(access_array, [])
        
        assert fn() == 2

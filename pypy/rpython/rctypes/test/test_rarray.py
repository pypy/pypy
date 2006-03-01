"""
Test the rctypes implementation.
"""

import py.test
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.translator.translator import TranslationContext
from pypy import conftest
import sys
from pypy.rpython.test.test_llinterp import interpret
from pypy.rpython.rctypes.test.test_rctypes import compile

try:
    import ctypes
except ImportError:
    py.test.skip("this test needs ctypes installed")

from pypy.rpython.rctypes import cdll, c_char_p, c_int, c_char, \
        c_char, c_byte, c_ubyte, c_short, c_ushort, c_uint,\
        c_long, c_ulong, c_longlong, c_ulonglong, c_float, c_double, \
        POINTER, Structure, byref, ARRAY

c_int_10 = ARRAY(c_int,10)
c_int_p_test = POINTER(c_int)

class Test_array:
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

    def test_annotate_pointer_access_as_array(self):
        """
        Make sure that pointers work the same way as arrays, for 
        ctypes compatibility.

        :Note: This works because pointer and array classes both
        have a _type_ attribute, that contains the type of the 
        object pointed to or in the case of an array the element type. 
        """
        def access_array():
            # Never run this function!
            # See test_annotate_pointer_access_as_array_or_whatever
            # for the weird reasons why this gets annotated
            my_pointer = c_int_p_test(10)
            my_pointer[0] = c_int(1)
            my_pointer[1] = 2

            return my_pointer[0]

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(access_array, [])
        assert s.knowntype == int
        #d#t.view()

    def test_annotate_array_slice_access(self):
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

    def test_specialize_array(self):
        def create_array():
                return c_int_10()

        res = interpret(create_array, [])
        c_data = res.c_data
        assert c_data[0] == 0
        assert c_data[9] == 0
        py.test.raises(IndexError, "c_data[10]")
        py.test.raises(TypeError, "len(c_data)")

    def test_specialize_array_access(self):
        def access_array():
            my_array = c_int_10()
            my_array[0] = 1

            return my_array[0]

        res = interpret(access_array, [])
        assert res == 1

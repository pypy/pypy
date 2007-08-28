"""
Test the numpy implementation.
"""

import py
import pypy.rpython.numpy.implementation
from pypy.annotation import model as annmodel
from pypy.annotation.model import SomeTuple
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.translator.translator import TranslationContext
from pypy import conftest
import sys
from pypy.rpython.test.test_llinterp import interpret
from pypy.rpython.lltypesystem import rffi
from pypy.rpython.rint import IntegerRepr
from pypy.rpython.numpy.rarray import ArrayRepr
from pypy.rpython.numpy.aarray import SomeArray

import numpy

test_c_compile = True
test_llvm_compile = False

def access_array(item):
    my_array = numpy.array([item])
    return my_array[0]

class Test_annotation:
    def test_annotate_array_access_int(self):
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(access_array, [int])
        assert s.knowntype == rffi.r_int

    def test_annotate_array_access_float(self):
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(access_array, [float])
        assert s.knowntype == float

        if conftest.option.view:
            t.view()

    def test_annotate_array_access_bytype(self):
        def access_array_bytype(dummy):
            my_array = numpy.array([1],'d')
            return my_array[0]

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(access_array_bytype, [int])
        assert s.knowntype == float

        if conftest.option.view:
            t.view()

    def test_annotate_array_access_variable(self):
        def access_with_variable():
            my_array = numpy.array(range(10))
            my_array[2] = 2
            sum = 0
            for idx in range(10):
                sum += my_array[idx]

            return sum

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(access_with_variable, [])
        assert s.knowntype == rffi.r_int

    def test_annotate_array_add(self):
        def f():
            a1 = numpy.array([1,2])
            a2 = numpy.array([6,9])
            return a1 + a2

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(f, [])
        assert s.typecode == 'i'

    def test_annotate_array_add_coerce(self):
        def f():
            a1 = numpy.array([1,2])
            a2 = numpy.array([6.,9.])
            return a1 + a2

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(f, [])
        assert s.typecode == 'd'

    def test_annotate_array_attr(self):
        def f():
            a1 = numpy.array([1,2])
            return a1.shape

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(f, [])
        assert type(s) == SomeTuple

    def test_annotate_array_method(self):
        def f():
            a1 = numpy.array([1,2])
            return a1.transpose()

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(f, [])
        assert type(s) == SomeArray



class Test_specialization:
    def test_specialize_array_create(self):
        def create_array():
            return numpy.array([1,2])

        res = interpret(create_array, [])
        assert res.data[0] == 1
        assert res.data[1] == 2

    def test_specialize_array_access(self):
        def access_with_variable():
            my_array = numpy.array(range(10))
            my_array[2] = 2
            sum = 0
            for idx in range(10):
                sum += my_array[idx]

            return sum

        res = interpret(access_with_variable, [])
        assert res == 45

    def test_specialize_array_add(self):
        def create_array():
            a1 = numpy.array([1,2])
            a2 = numpy.array([6,9])
            return a1 + a2

        res = interpret(create_array, [])
        assert res.data[0] == 7
        assert res.data[1] == 11

    def test_specialize_array_attr(self):
        def create_array():
            a = numpy.array([1,2])
            return a.ndim

        res = interpret(create_array, [])
        assert res == 1

    def test_specialize_array_method(self):
        def create_array():
            a = numpy.array([1,2])
            return a.transpose()

        res = interpret(create_array, [])
        assert res.data[0] == 1
        assert res.data[1] == 2

class Test_compile:
    def setup_class(self):
        if not test_c_compile:
            py.test.skip("c compilation disabled")

        from pypy.translator.c.test.test_genc import compile
        self.compile = lambda s, x, y : compile(x, y)

    def test_compile_array_access(self):
        def access_array(index):
            my_array = numpy.array([3,99,2])
            my_array[0] = 1
            return my_array[index]

        fn = self.compile(access_array, [int])
        assert fn(0) == 1
        assert fn(1) == 99
        


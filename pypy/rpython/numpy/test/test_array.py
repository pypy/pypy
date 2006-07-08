"""
Test the array implementation.
"""

import py
import pypy.rpython.numpy.implementation
from pypy.annotation import model as annmodel
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.translator.translator import TranslationContext
from pypy import conftest
import sys
from pypy.rpython.test.test_llinterp import interpret

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
        assert s.knowntype == int

    def test_annotate_array_access_float(self):
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(access_array, [float])
        assert s.knowntype == float

        if conftest.option.view:
            t.view()

    def test_annotate_array_access_bytype(self):
        def access_array_bytype(dummy):
            my_array = numpy.array([1],'f')
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
        assert s.knowntype == int

class Test_specialization:
    def test_specialize_array(self):
        def create_array():
            return numpy.array([1,2])

        res = interpret(create_array, [])

        print res
#        c_data = res.c_data
#        assert c_data[0] == 0
#        assert c_data[1] == 0
#        py.test.raises(IndexError, "c_data[2]")
#        assert len(c_data) == 2

#    def test_specialize_array_access(self):
#        def access_array(n):
#            my_array = c_int_10()
#            my_array[0] = 1
#            my_array[1] = c_int(1)
#            my_array[2] = n
#
#            return my_array[0]
#
#        res = interpret(access_array, [44])
#        assert res == 1

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
#            my_array[1] = 99
#            return my_array[1]
            return my_array[index]

        fn = self.compile(access_array, [int])
        assert fn(0) == 1
        assert fn(1) == 99
        
        t = TranslationContext()
        t.buildannotator().build_types(access_array, [int])
        t.buildrtyper().specialize()
        graph = t.buildflowgraph(access_array)
        
        from pypy.translator.tool.make_dot import make_dot
        filename = make_dot('access_array', graph)

        from pypy.translator.c.genc import CExtModuleBuilder
        b = CExtModuleBuilder(t, access_array)
        filename = b.generate_source()


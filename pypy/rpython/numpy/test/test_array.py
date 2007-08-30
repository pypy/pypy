"""
Test the numpy implementation.
"""

import py
import pypy.rpython.numpy.implementation
from pypy.annotation import model as annmodel
from pypy.annotation.model import SomeObject, SomeTuple
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.tool.error import AnnotatorError
from pypy.translator.translator import TranslationContext, graphof
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

    def test_annotate_zeros(self):
        def f():
            a = numpy.zeros((3,4,5))
            return a

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(f, [])
        assert s.typecode == 'd'
        assert s.ndim == 3

    def test_annotate_indexing(self):
        def f():
            a = numpy.zeros((3,4,5))
            b = a[0]
            a[0,1,2] = 1.
            b[0,1] = 2.
            b[:] = a[1]
            b[:,:] = a[1]
            b[0,:] = a[1,2]
            return b

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(f, [])
        assert s.ndim == 2

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

    def test_annotate_array_dtype(self):
        def f():
            a1 = numpy.array([1,2], dtype='d')
            return a1

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(f, [])
        assert s.typecode == 'd'

    def test_annotate_array_array(self):
        def f():
            a1 = numpy.array([1,2], dtype='d')
            a2 = numpy.array(a1)
            return a2

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

from pypy.objspace.flow.model import checkgraph, flatten, Block, mkentrymap
from pypy.translator.backendopt.malloc import LLTypeMallocRemover

class Test_specialization:
    def test_specialize_array_create(self):
        def create_array():
            a = numpy.array([1,20])
            b = numpy.array(a)
            return b

        res = interpret(create_array, [])
        assert res.data[0] == 1
        assert res.data[1] == 20

    def test_specialize_array_zeros(self):
        def create_array(n, m):
            a = numpy.zeros((n, m))
            return a

        res = interpret(create_array, [3, 4])
        assert res.ndim == 2

    def test_specialize_array_access(self):
        def access_with_variable():
            my_array = numpy.array(range(10), dtype='i')
            my_array[2] = 2
            sum = 0
            for idx in range(10):
                sum += my_array[idx]

            return sum

        res = interpret(access_with_variable, [])
        assert res == 45

    def test_specialize_array_add(self):
        def create_array():
            a1 = numpy.array([1.,2.])
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

    def test_specialize_array_attr_shape(self):
        def create_array():
            a = numpy.zeros((2,3))
            return list(a.shape)

        res = interpret(create_array, [])
        assert res[0] == 2
        assert res[1] == 3

    def test_specialize_array_strides(self):
        def create_array():
            a = numpy.zeros((3,4,5))
            return a

        res = interpret(create_array, [])
        assert res.strides[0] == 20
        assert res.strides[1] == 5
        assert res.strides[2] == 1
        #assert len(res.data) == 3*4*5 # GcArray has nolength

    def test_specialize_array_method(self):
        def create_array():
            a = numpy.array([1,2])
            return a.transpose()

        res = interpret(create_array, [])
        assert res.data[0] == 1
        assert res.data[1] == 2

    def test_specialize_indexing(self):
        def f():
            a = numpy.zeros((3,), dtype='i')
            b = numpy.array([5,55,555])
            a[:] = b
            return a
        res = interpret(f, [])
        assert res.data[0] == 5
        assert res.data[1] == 55
        assert res.data[2] == 555

    def specialize_view(self, f, args=[]):
        t = TranslationContext()
        a = t.buildannotator()
        a = a.build_types(f, args)
        r = t.buildrtyper()
        r.specialize()
        from pypy.translator.backendopt.all import backend_optimizations
        backend_optimizations(t)
        t.view()

    def test_malloc_remove(self):
        def f():
            a = numpy.zeros((3,), dtype='i')
            b = numpy.array([5,55,555])
            a[:] = b
            return a
        t = TranslationContext()
        a = t.buildannotator()
        a = a.build_types(f, [])
        r = t.buildrtyper()
        r.specialize()
        from pypy.translator.backendopt.all import backend_optimizations
        backend_optimizations(t)
        from pypy.rpython.numpy.rarray import ll_setitem_from_array
        graph = graphof(t, ll_setitem_from_array)
        #graph.show()
        from pypy.translator.backendopt.test.test_malloc import TestLLTypeMallocRemoval
        TestLLTypeMallocRemoval.check_malloc_removed(graph)



class Test_compile:
    def setup_class(self):
        if not test_c_compile:
            py.test.skip("c compilation disabled")

        from pypy.translator.c.test.test_genc import compile
        self.compile = lambda s, x, y : compile(x, y)

    def test_compile_array_access(self):
        def access_array(index):
            a = numpy.zeros((3,), dtype='i')
            b = numpy.array([5,55,555])
            a[:] = b
            a[0] = 1
            return a[index]

        fn = self.compile(access_array, [int])
        assert fn(0) == 1
        assert fn(1) == 55
        assert fn(2) == 555
        
    def test_compile_2d(self):
        py.test.skip()
        def access_array(index):
            a = numpy.zeros((5,6))
            a[0,0] = 2
            return 0

        fn = self.compile(access_array, [int])
        


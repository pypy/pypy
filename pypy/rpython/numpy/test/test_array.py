"""
Test the numpy implementation.
"""

import py
import pypy.rpython.numpy.implementation
from pypy.annotation import model as annmodel
from pypy.annotation.model import SomeObject, SomeInteger, SomeChar, SomeTuple
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.tool.error import AnnotatorError
from pypy.translator.translator import TranslationContext, graphof
from pypy import conftest
import sys
from pypy.rpython.test.test_llinterp import interpret
from pypy.rpython.lltypesystem import rffi
from pypy.rpython.rint import IntegerRepr

def setup_module(mod):
    try:
        import numpy
    except ImportError:
        py.test.skip("numpy not found")
    mod.numpy = numpy

from pypy.rpython.numpy.rarray import ArrayRepr
from pypy.rpython.numpy.aarray import SomeArray

test_c_compile = True


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

    def test_annotate_attr(self):
        def f():
            a = numpy.empty((3,4,5))
            return a.ndim

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(f, [])
        assert isinstance(s, SomeInteger)

        def f():
            a = numpy.empty((3,4,5))
            return a.shape

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(f, [])
        assert isinstance(s, SomeTuple)

        def f():
            a = numpy.empty((3,4,5))
            return a.dtype

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(f, [])
        assert isinstance(s, SomeChar)

    def test_annotate_empty(self):
        def f():
            a = numpy.empty((3,4,5))
            return a

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(f, [])
        assert s.typecode == 'd'
        assert s.ndim == 3

    def test_annotate_indexing(self):
        def f():
            a = numpy.empty((3,4,5))
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

    def test_annotate_array_add_list(self):
        def f():
            a1 = numpy.array([1,2])
            a2 = [3., 4.]
            return a1 + a2

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(f, [])
        assert s.typecode == 'd'

    def test_annotate_array_add_coerce(self):
        def f():
            a1 = numpy.array([1,2])
            a2 = numpy.array([6.,9.])
            return a1 + a2

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(f, [])
        assert s.typecode == 'd'

    def test_annotate_array_add_scalar(self):
        def f():
            a = numpy.array([1,2])
            a = a + 3
            return a

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(f, [])
        assert s.typecode == 'i'

    def test_annotate_array_add_scalar_coerce(self):
        def f():
            a = numpy.array([1,2])
            return a + 3.

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(f, [])
        assert s.typecode == 'd'

    def test_annotate_array_inplace_add_list(self):
        def f():
            a = numpy.array([1,2,3,4])
            a += [4,3,2,1]
            return a

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(f, [])
        assert s.typecode == 'l'

    def test_annotate_array_inplace_mul_coerce(self):
        def f():
            a = numpy.array([1,2,3,4])
            a *= 0.5
            return a

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(f, [])
        assert s.typecode == 'l'

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
        def fget():
            a1 = numpy.array([1,2])
            return a1.shape

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(fget, [])
        assert type(s) == SomeTuple

    def test_annotate_array_method(self):
        def f_transpose():
            a = numpy.zeros((3,4))
            return a.transpose()

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(f_transpose, [])
        assert type(s) == SomeArray
        assert s.ndim == 2

        def f_reshape():
            a = numpy.array(range(12))
            return a.reshape((3,4))

        s = a.build_types(f_reshape, [])
        assert type(s) == SomeArray
        assert s.ndim == 2

        def f_astype():
            a = numpy.array(range(12))
            return a.astype('d')

        s = a.build_types(f_astype, [])
        assert type(s) == SomeArray
        assert s.ndim == 1
        assert s.typecode == 'd'

        def f_copy():
            a = numpy.array(range(12))
            return a.copy()

        s = a.build_types(f_copy, [])
        assert type(s) == SomeArray
        assert s.ndim == 1
        assert s.typecode == 'l'

    def test_annotate_indexing(self):
        def f():
            a = numpy.empty((4,3), dtype='i')
            c = a[:,0]
            return c
        t = TranslationContext()
        a = t.buildannotator()
        s_array = a.build_types(f, [])
        assert type(s_array) == SomeArray
        assert s_array.ndim == 1

    def test_annotate_broadcast(self):
        def f():
            a = numpy.empty((4,3), dtype='i')
            b = numpy.array([33])
            a[:] = b
            return a
        t = TranslationContext()
        a = t.buildannotator()
        s_array = a.build_types(f, [])
        assert type(s_array) == SomeArray
        assert s_array.ndim == 2



from pypy.objspace.flow.model import checkgraph, flatten, Block, mkentrymap
from pypy.translator.backendopt.malloc import LLTypeMallocRemover

class Test_specialization:
    def specialize_view(self, f, args=[], opt=False):
        t = TranslationContext()
        a = t.buildannotator()
        a = a.build_types(f, args)
        r = t.buildrtyper()
        r.specialize()
        if opt:
            from pypy.translator.backendopt.all import backend_optimizations
            backend_optimizations(t)
        t.view()

    def test_specialize_array_create(self):
        def f():
            a = numpy.array([1,20])
            b = numpy.array(a)
            return b

        res = interpret(f, [])
        assert res.data[0] == 1
        assert res.data[1] == 20

    def test_specialize_array_empty1(self):
        def f(n):
            a = numpy.empty(n)
            return a

        res = interpret(f, [3])
        assert res.ndim == 1

    def test_specialize_array_empty(self):
        def f(n, m):
            a = numpy.empty((n, m))
            return a

        res = interpret(f, [3, 4])
        assert res.ndim == 2

    def test_specialize_array_zeros(self):
        def f(n, m):
            a = numpy.zeros((n, m))
            return a

        res = interpret(f, [3, 4])
        for i in range(3*4):
            assert res.dataptr[i] == 0
        assert res.ndim == 2

    def test_specialize_array_attr(self):
        def f():
            a = numpy.empty((3,4,5))
            return a.ndim
        res = interpret(f, [])
        assert res == 3

        def f():
            a = numpy.empty((3,4,5))
            return a.shape
        res = interpret(f, [])
        assert res.item0 == 3
        assert res.item1 == 4
        assert res.item2 == 5

        def f():
            a = numpy.empty((3,4,5))
            return a.dtype
        res = interpret(f, [])
        assert res == 'd'


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

    def test_specialize_array_attr_shape(self):
        def f():
            a = numpy.empty((2,3))
            return list(a.shape)

        res = interpret(f, [])
        assert res[0] == 2
        assert res[1] == 3

    def test_specialize_array_strides(self):
        def f():
            a = numpy.empty((3,4,5))
            return a

        res = interpret(f, [])
        # Note that the real numpy defines strides to be a byte-count
        # but we return an element count ATM.
        assert res.strides[0] == 20
        assert res.strides[1] == 5
        assert res.strides[2] == 1
        #assert len(res.data) == 3*4*5 # GcArray has nolength

    def test_specialize_array_method(self):
        def f_transpose():
            a = numpy.zeros((3,4))
            return a.transpose()

        res = interpret(f_transpose, [])
        assert res.shape[0] == 4
        assert res.shape[1] == 3

        def f_reshape():
            a = numpy.array(range(12))
            b = a.reshape((3,4))
            b[1,2] = 0
            return b

        res = interpret(f_reshape, [])
        assert res.shape[0] == 3
        assert res.shape[1] == 4
        assert res.strides[0] == 4
        assert res.strides[1] == 1
        assert res.dataptr[5] == 5
        assert res.dataptr[6] == 0

        def f_astype():
            a = numpy.array(range(12))
            b = a.astype('d')
            b = b/2
            return b

        res = interpret(f_astype, [])
        assert res.dataptr[0] == 0.
        assert res.dataptr[1] == 0.5

        def f_copy():
            a = numpy.array(range(4))
            b = a.copy()
            a[:] = 0
            return b

        res = interpret(f_copy, [])
        for i in range(4):
            assert res.dataptr[i] == i

    def test_specialize_view_0(self):
        def f():
            a = numpy.empty((4,3), dtype='i')
            a[0,0] = 5
            a[1,0] = 55
            a[2,0] = 555
            c = a[:,0]
            return c
        res = interpret(f, [])
        assert res.dataptr[0] == 5
        assert res.dataptr[3] == 55
        assert res.dataptr[6] == 555
        assert res.shape.item0 == 4
        assert res.strides.item0 == 3
        assert res.ndim == 1

    def test_specialize_multi(self):
        def f(ii, jj):
            a = numpy.empty((4, 5), dtype='i')
            for i in range(4):
                for j in range(5):
                    a[i, j] = i*j
            return a[ii, jj]
        assert interpret(f, [0, 0]) == 0
        assert interpret(f, [3, 4]) == 12

    def test_specialize_list_rhs(self):
        def f():
            a = numpy.zeros((3,4), dtype='i')
            a[:] = [3,4,4,2]
            return a
        res = interpret(f, [])
        data = [3,4,4,2]*3
        for i in range(len(data)):
            assert res.dataptr[i] == data[i]

    def test_specialize_list_coerce(self):
        def f():
            a = numpy.zeros((3,4), dtype='i')
            a[:] = [3.,4.,4.,2.]
            return a
        res = interpret(f, [])
        data = [3,4,4,2]*3
        for i in range(len(data)):
            assert res.dataptr[i] == data[i]

    def test_specialize_rhs_coerce(self):
        def f():
            a = numpy.zeros((4,), dtype='i')
            b = numpy.array([3.,4.,4.,2.])
            a[:] = b
            return a
        res = interpret(f, [])
        data = [3,4,4,2]
        for i in range(len(data)):
            assert res.dataptr[i] == data[i]

    def test_specialize_slice_1_0(self):
        def f():
            a = numpy.zeros((12,), dtype='i')
            a[:2] = 1
            a[5:9] = 2
            a[10:] = 3
            a[12:] = 99
            a[12:0] = 999
            return a
        res = interpret(f, [])
        data = [1,1,0,0,0,2,2,2,2,0,3,3]
        for i in range(12):
            assert res.dataptr[i] == data[i]

    def test_specialize_slice_1_1(self):
        # This involves a runtime test to see if we need a broadcast iterator
        def f():
            a = numpy.zeros((6,), dtype='i')
            a[:2] = numpy.array([1])
            a[5:9] = numpy.array([2])
            return a
        res = interpret(f, [])
        data = [1,1,0,0,0,2]
        for i in range(6):
            assert res.dataptr[i] == data[i]

    def test_specialize_slice_2_0(self):
        def f():
            a = numpy.zeros((12,), dtype='i').reshape((3,4))
            a[:2, :1] = 1
            return a
        res = interpret(f, [])
        data = [1,0,0,0,1,0,0,0,0,0,0,0]
        for i in range(12):
            assert res.dataptr[i] == data[i]

    def test_specialize_slice_2_1(self):
        def f():
            a = numpy.zeros((12,), dtype='i').reshape((3,4))
            a[:2, 0] = numpy.array([1,2])
            a[1, 1:3] = numpy.array([4,5])
            a[0:1, 3:] = numpy.array([6,])
            return a
        res = interpret(f, [])
        data = [1, 0, 0, 6, 2, 4, 5, 0, 0, 0, 0, 0]
        for i in range(12):
            assert res.dataptr[i] == data[i]

    def test_specialize_slice_2_2(self):
        def f():
            a = numpy.zeros((12,), dtype='i').reshape((3,4))
            b = numpy.array([1,2,3,4]).reshape((2,2))
            a[1:3, 2:] = b
            return a
        res = interpret(f, [])
        data = [0, 0, 0, 0, 0, 0, 1, 2, 0, 0, 3, 4]
        for i in range(12):
            assert res.dataptr[i] == data[i]

    def test_specialize_view(self):
        def f(ii, jj):
            a = numpy.zeros((4, 5))
            b = numpy.zeros((3, 4))
            a[0,1] = 5.
            a[1,1] = 4.
            a[2,1] = 3.
            a[3,1] = 2.
            b[2,:] = a[:,1]
            return b[ii, jj]

        assert interpret(f, [2, 3]) == 2
        
    def test_specialize_view_implicit_slice(self):
        def f():
            a = numpy.array(range(12)).reshape((3,4))
            b = a[0,]
            return b

        res = interpret(f, [])
        for i in range(4):
            assert res.dataptr[i] == i
        
    def test_specialize_broadcast(self):
        def f():
            a = numpy.empty((4,3), dtype='i')
            b = numpy.array([33])
            a[:,:] = b
            return a
        res = interpret(f, [])
        for i in range(4*3):
            assert res.dataptr[i] == 33

        def f():
            a = numpy.empty((4,3), dtype='i')
            b = numpy.array([33])
            a[:,] = b
            return a
        res = interpret(f, [])
        for i in range(4*3):
            assert res.dataptr[i] == 33

        def f():
            a = numpy.empty((4,3,2), dtype='i')
            a[:] = numpy.array([33])
            a[0,:] = numpy.array([22])
            return a
        res = interpret(f, [])
        data = [22]*6 + [33]*18
        for i in range(3*4*2):
            assert res.dataptr[i] == data[i]

    def test_malloc_remove(self):
        def f():
            a = numpy.empty((3,), dtype='i')
            b = numpy.array([5,55,555], dtype='i')
            a[:] = b
            return a
        t = TranslationContext()
        a = t.buildannotator()
        a = a.build_types(f, [])
        r = t.buildrtyper()
        r.specialize()
        from pypy.translator.backendopt.all import backend_optimizations
        backend_optimizations(t)
        from pypy.rpython.numpy.rarray import ll_array_set
        graph = graphof(t, ll_array_set)
        #graph.show()
        from pypy.translator.backendopt.test.test_malloc import TestLLTypeMallocRemoval
        TestLLTypeMallocRemoval.check_malloc_removed(graph)

    def test_specialize_array_add_1_0(self):
        def f():
            a1 = numpy.array(range(4,10))
            a2 = numpy.array([3])
            return a1 + a2
        data = [i+3 for i in range(4,10)]
        res = interpret(f, [])
        for i in range(len(data)):
            assert res.dataptr[i] == data[i]

        def f():
            a = numpy.array(range(4,10))
            return a + 3
        res = interpret(f, [])
        for i in range(len(data)):
            assert res.dataptr[i] == data[i]

        def f():
            a = numpy.array(range(4,10))
            return 3 + a
        res = interpret(f, [])
        for i in range(len(data)):
            assert res.dataptr[i] == data[i]

    def test_specialize_array_sub_1_0(self):
        def f():
            a1 = numpy.array(range(4,10))
            a2 = numpy.array([3])
            return a1 - a2
        data = [i-3 for i in range(4,10)]
        res = interpret(f, [])
        for i in range(len(data)):
            assert res.dataptr[i] == data[i]

        def f():
            a = numpy.array(range(4,10))
            return a - 3
        res = interpret(f, [])
        for i in range(len(data)):
            assert res.dataptr[i] == data[i]

        def f():
            a = numpy.array(range(4,10))
            return 3 - a
        data = [3-i for i in range(4,10)]
        res = interpret(f, [])
        for i in range(len(data)):
            assert res.dataptr[i] == data[i]


    def test_specialize_array_add_1_1(self):
        def f():
            a1 = numpy.array([1,2])
            a2 = numpy.array([6,9])
            return a1 + a2

        res = interpret(f, [])
        assert res.data[0] == 7
        assert res.data[1] == 11

    def test_specialize_array_add_1_1_coerce(self):
        def f():
            a1 = numpy.array([1,2])
            a2 = numpy.array([6.5,9.5])
            return a1 + a2

        res = interpret(f, [])
        assert res.data[0] == 7.5
        assert res.data[1] == 11.5

    def test_specialize_array_add_1_1_coerce_from_list(self):
        def f():
            a1 = numpy.array([1,2])
            a2 = [6.5,9.5]
            return a1 + a2

        res = interpret(f, [])
        assert res.data[0] == 7.5
        assert res.data[1] == 11.5

    def test_specialize_array_add_1_1_coerce_from_scalar(self):
        def f():
            a = numpy.array([1,2])
            return a + 1.5

        res = interpret(f, [])
        assert res.data[0] == 2.5
        assert res.data[1] == 3.5

    def test_specialize_array_add_2_1(self):
        def f():
            a1 = numpy.array([1,2,3,4]).reshape((2,2))
            a2 = numpy.array([5,6])
            return a1 + a2

        res = interpret(f, [])
        data = [6,8,8,10]
        for i in range(len(data)):
            assert res.dataptr[i] == data[i]
        assert res.shape[0] == 2
        assert res.shape[1] == 2
        assert res.strides[0] == 2
        assert res.strides[1] == 1

    def test_specialize_array_mul_0_2(self):
        def f():
            a = numpy.array([1,2,3,4]).reshape((2,2))
            return 5*a

        res = interpret(f, [])
        data = [1,2,3,4]
        for i in range(len(data)):
            assert res.dataptr[i] == 5*data[i]

    def test_specialize_array_add_list(self):
        def f():
            a = numpy.array([1,2,3,4])
            a = a + [4,3,2,1]
            return a

        res = interpret(f, [])
        for i in range(4):
            assert res.dataptr[i] == 5

    def test_specialize_array_radd_list(self):
        def f():
            a = numpy.array([1,2,3,4])
            a = [4,3,2,1] + a
            return a

        res = interpret(f, [])
        for i in range(4):
            assert res.dataptr[i] == 5

    def test_specialize_array_inplace_add(self):
        def f():
            a = numpy.array([1,2,3,4])
            a += 1
            return a

        res = interpret(f, [])
        data = [1,2,3,4]
        for i in range(len(data)):
            assert res.dataptr[i] == data[i] + 1

    def test_specialize_array_inplace_add_list_broadcast(self):
        def f():
            a = numpy.array([1,2,3,4]).reshape((2,2))
            a += [0,1]
            return a

        res = interpret(f, [])
        data = [1,3,3,5]
        for i in range(len(data)):
            assert res.dataptr[i] == data[i]

    def test_specialize_array_inplace_mul_coerce(self):
        def f():
            a = numpy.array([1,2,3,4])
            a *= numpy.array([0.5])
            return a

        res = interpret(f, [])
        data = [1,2,3,4]
        for i in range(len(data)):
            assert res.dataptr[i] == data[i]//2

    def test_specialize_array_inplace_mul_coerce_from_list(self):
        def f():
            a = numpy.array([1,2])
            a *= [1.5, 2.5]
            return a

        res = interpret(f, [])
        data = [1.0, 5.0]
        for i in range(len(data)):
            assert res.dataptr[i] == data[i]

    def test_specialize_array_inplace_mul_coerce_from_scalar(self):
        def f():
            a = numpy.array([1,2,3,4])
            a *= 0.5
            return a

        res = interpret(f, [])
        data = [1,2,3,4]
        for i in range(len(data)):
            assert res.dataptr[i] == data[i]//2

    def test_specialize_array_setitem_alias(self):
        py.test.skip('not implemented')
        def f():
            a = numpy.array([1,2,3,4])
            a[1:] = a[:3]
            return a

        res = interpret(f, [])
        data = [1,1,2,3]
        for i in range(len(data)):
            assert res.dataptr[i] == data[i]

    def test_specialize_array_inplace_add_alias(self):
        py.test.skip('not implemented')
        def f():
            a = numpy.array([1,2,3,4])
            a[1:] += a[:3]
            return a

        res = interpret(f, [])
        data = [1,3,5,7]
        for i in range(len(data)):
            assert res.dataptr[i] == data[i]

"""
TODO (maybe):
* indexing with ellipses
* indexing with newaxis
* unary plus operator (does a copy)
* advanced selection: indexing with bool/int arrays (or lists)
"""

class Test_compile:
    def setup_class(self):
        if not test_c_compile:
            py.test.skip("c compilation disabled")

        from pypy.translator.c.test.test_genc import compile
        self.compile = lambda s, x, y : compile(x, y, backendopt=True)

    def test_compile_array_access(self):
        def access_array(index):
            a = numpy.empty((3,), dtype='i')
            b = numpy.array([5,55,555], dtype='i')
            a[:] = b
            a[0] = 1
            return a[index]

        fn = self.compile(access_array, [int])
        assert fn(0) == 1
        assert fn(1) == 55
        assert fn(2) == 555
        
    def test_compile_2d(self):
        def f(ii, jj):
            a = numpy.empty((4, 5), dtype='i')
            for i in range(4):
                for j in range(5):
                    a[i, j] = i*j
            return a[ii, jj]

        fn = self.compile(f, [int, int])
        for i in range(4):
            for j in range(5):
                assert fn(i, j) == i*j
        
    def test_compile_view(self):
        def f(ii, jj):
            a = numpy.zeros((4, 5), dtype='i')
            b = numpy.zeros((3, 4), dtype='i')
            b[0,:] = a[:,0]
            return b[ii, jj]

        fn = self.compile(f, [int, int])
        assert fn(2,3) == 0
        



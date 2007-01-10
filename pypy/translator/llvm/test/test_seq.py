from __future__ import division

import py
from pypy.objspace.flow.model import Constant, Variable
from pypy.translator.llvm.test import llvmsnippet

from pypy.translator.llvm.test.runtest import *

class TestLLVMArray(object):
    def test_char_array(self):
        from pypy.rpython.lltypesystem import lltype
        A = lltype.GcArray(lltype.Char)
        def fn(n):
            a = lltype.malloc(A, 5)
            a[4] = 'H'
            a[3] = 'e'
            a[2] = 'l'
            a[1] = 'l'
            a[0] = 'o'
            return ord(a[n]) 
        fp = compile_function(fn, [int])
        for i in range(5):
            assert fp(i) == fn(i)

    def test_array(self):
        f = compile_function(llvmsnippet.array_simple, [])
        assert f() == 42

    def test_array1(self):
        f = compile_function(llvmsnippet.array_simple1, [int])
        assert f(1) == 10
        assert f(-42) == -420

    def test_array_setitem(self):
        f = compile_function(llvmsnippet.array_setitem, [int])
        assert f(1) == 12
        assert f(2) == 13
        assert f(3) == 3

    def test_array_add(self):
        f = compile_function(llvmsnippet.array_add, [int, int, int, int, int])
        assert f(1,2,3,4,0) == 1
        assert f(1,2,3,4,1) == 2
        assert f(1,2,3,4,2) == 3
        assert f(1,2,5,6,3) == 6

    def test_array_double(self):
        f = compile_function(llvmsnippet.double_array, [])
        assert f() == 15

    def test_bool_array(self):
        f = compile_function(llvmsnippet.bool_array, [])
        assert f() == 1

    def test_array_arg(self):
        f = compile_function(llvmsnippet.array_arg, [int])
        assert f(5) == 0

    def test_array_len(self):
        f = compile_function(llvmsnippet.array_len, [])
        assert f() == 10

    def test_array_append(self):
        f = compile_function(llvmsnippet.array_append, [int])
        for i in range(3):
            assert f(i) == 0
        assert f(3) == 10

    def test_array_reverse(self):
        f = compile_function(llvmsnippet.array_reverse, [int])
        assert f(0) == 1
        assert f(1) == 0

    def test_range(self):
        f = compile_function(llvmsnippet.rangetest, [int])
        for i in range(10):
            assert f(i) == i

    def test_array_pop(self):
        f = compile_function(llvmsnippet.array_pop, [int])
        assert f(0) == 6
        assert f(1) == 7
        assert f(2) == 8

    def test_newlist_zero_arg(self):
        f = compile_function(llvmsnippet.newlist_zero_arg, [int])
        assert f(10) == 11
        assert f(-41) == -40

    def test_big_array(self):
        f = compile_function(llvmsnippet.big_array, [int])
        for i in range(18):
            assert f(i) == i

    def test_access_global_array(self):
        f = compile_function(llvmsnippet.access_global_array, [int, int, int])
        for i in range(5):
            for j in range(5):
                assert f(i, j, i + j) == i
        for i in range(5):
            for j in range(5):
                assert f(i, j, 0) == i + j

    def test_circular_list(self):
        f = compile_function(llvmsnippet.circular_list, [int])
        assert f(0) == 0
        assert f(1) == 1
        assert f(10) == 1


class TestTuple(object):
    def test_f1(self):
        f = compile_function(llvmsnippet.tuple_f1, [int])
        assert f(10) == 10
        assert f(15) == 15

    def test_f3(self):
        f = compile_function(llvmsnippet.tuple_f3, [int])
        assert f(10) == 10
        assert f(15) == 15
        assert f(30) == 30

    def test_constant_tuple(self):
        f = compile_function(llvmsnippet.constant_tuple, [int])
        for i in range(3, 7):
            assert f(i) == i + 3

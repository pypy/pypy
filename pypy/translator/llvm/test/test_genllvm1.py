from __future__ import division
import sys

import py
from pypy.objspace.flow.model import Constant, Variable
from pypy.translator.llvm.test import llvmsnippet

from pypy.translator.llvm.test.runtest import *

class TestGenLLVM(object):
    def test_simple1(self):
        f = compile_function(llvmsnippet.simple1, [])
        assert f() == 1

    def test_simple2(self):
        f = compile_function(llvmsnippet.simple2, [])
        assert f() == 0

    def test_simple4(self):
        f = compile_function(llvmsnippet.simple4, [])
        assert f() == 4

    def test_simple5(self):
        f = compile_function(llvmsnippet.simple5, [int])
        assert f(1) == 12
        assert f(0) == 13

    def test_ackermann(self):
        f = compile_function(llvmsnippet.ackermann, [int, int])
        for i in range(10):
            assert f(0, i) == i + 1
            assert f(1, i) == i + 2
            assert f(2, i) == 2 * i + 3
            assert f(3, i) == 2 ** (i + 3) - 3

    def test_calling(self):
        f = compile_function(llvmsnippet.calling1, [int])
        assert f(10) == 1

    def test_call_default_arguments(self):
        f = compile_function(llvmsnippet.call_default_arguments, [int, int])
        for i in range(3):
            assert f(i + 3, i) == llvmsnippet.call_default_arguments(i + 3, i)

    def test_call_list_default_argument(self):
        f = compile_function(llvmsnippet.call_list_default_argument, [int])
        for i in range(20):
            assert f(i) == llvmsnippet.call_list_default_argument(i)

    def test_shift(self):
        shl = compile_function(llvmsnippet.shiftleft, [int, int])
        shr = compile_function(llvmsnippet.shiftright, [int, int])
        assert shl(42,2) == llvmsnippet.shiftleft(42, 2)
        assert shr(42,2) == llvmsnippet.shiftright(42,2)

class TestFloat(object):
    def _almost_equal(self, a, b):
        _epsilon = 0.0000001
        return a >= b - _epsilon and a <= b + _epsilon

    def test_float_f1(self):
        f = compile_function(llvmsnippet.float_f1, [float])
        assert self._almost_equal(f(1.0), 2.2)

    def test_float_int_bool(self):
        f = compile_function(llvmsnippet.float_int_bool, [float])
        assert self._almost_equal(f(3.0), 9.0)


class TestString(object):
    def test_f2(self):
        f = compile_function(llvmsnippet.string_f2, [int, int])
        assert f(1, 0) == "a"


class TestPBC(object):
    def test_pbc_function1(self):
        f = compile_function(llvmsnippet.pbc_function1, [int])
        assert f(0) == 2
        assert f(1) == 4
        assert f(2) == 6
        assert f(3) == 8

    def test_pbc_function2(self):
        f = compile_function(llvmsnippet.pbc_function2, [int])
        assert f(0) == 13
        assert f(1) == 15
        assert f(2) == 17
        assert f(3) == 19


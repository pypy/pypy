from __future__ import division

import py
from pypy.objspace.flow.model import Constant, Variable
from pypy.translator.llvm.test import llvmsnippet

from pypy.translator.llvm.test.runtest import *

class TestClass(object):
    def test_classsimple(self):
        f = compile_function(llvmsnippet.class_simple, [])
        assert f() == 14

    def test_classsimple1(self):
        f = compile_function(llvmsnippet.class_simple1, [int])
        assert f(2) == 10

    def test_id_int(self):
        f = compile_function(llvmsnippet.id_int, [int])
        for i in range(1, 20):
            assert f(i) == i

    def test_classsimple2(self):
        f = compile_function(llvmsnippet.class_simple2, [int])
        assert f(2) == 10

    def test_inherit1(self):
        f = compile_function(llvmsnippet.class_inherit1, [])
        assert f() == 11

    def test_inherit2(self):
        f = compile_function(llvmsnippet.class_inherit2, [])
        assert f() == 1

    def test_method_of_base_class(self):
        f = compile_function(llvmsnippet.method_of_base_class, [])
        assert f() == 14

    def test_attribute_from_base_class(self):
        f = compile_function(llvmsnippet.attribute_from_base_class, [])
        assert f() == 4

    def test_direct_call_of_virtual_method(self):
        f = compile_function(llvmsnippet.direct_call_of_virtual_method, [])
        assert f() == 14

    def test_flow_type(self):
        f = compile_function(llvmsnippet.flow_type, [])
        assert f() == 16

    def test_merge_class(self):
        f = compile_function(llvmsnippet.merge_classes, [bool])
        assert f(True) == 1
        assert f(False) == 2

    def test_attribute_instance(self):
        f = compile_function(llvmsnippet.attribute_instance, [bool])
        assert f(True) == 1
        assert f(False) == 2

    def test_global_instance(self):
        f = compile_function(llvmsnippet.global_instance, [int])
        assert f(-1) == llvmsnippet.global_instance(-1)
        for i in range(20):
            x = f(i)
            y = llvmsnippet.global_instance(i)
            assert x == y

    def test_getset(self):
        f = compile_function(llvmsnippet.testgetset, [int])
        assert f(15) == 25

    def test_call_degrading_func(self):
        f = compile_function(llvmsnippet.call_degrading_func, [bool])
        assert f(True) == llvmsnippet.call_degrading_func(True)
        assert f(False) == llvmsnippet.call_degrading_func(False)
    
    def test_circular_classdef(self):
        f = compile_function(llvmsnippet.circular_classdef, [])
        assert f() == 10

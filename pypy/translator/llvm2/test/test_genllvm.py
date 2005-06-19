from __future__ import division

import sys
import py

from pypy.translator.translator import Translator
from pypy.translator.llvm2.genllvm import genllvm
from pypy.translator.llvm2.test import llvmsnippet
from pypy.objspace.flow.model import Constant, Variable

from pypy.rpython.rtyper import RPythonTyper

py.log.setconsumer("genllvm", py.log.STDOUT)
py.log.setconsumer("genllvm database prepare", None)


## def setup_module(mod):
##     mod.llvm_found = is_on_path("llvm-as")

def compile_function(function, annotate):
    t = Translator(function)
    a = t.annotate(annotate)
    t.specialize()
    a.simplify()
    return genllvm(t)


def test_return1():
    def simple1():
        return 1
    f = compile_function(simple1, [])
    assert f() == 1

def test_simple_branching():
    def simple5(b):
        if b:
            x = 12
        else:
            x = 13
        return x
    f = compile_function(simple5, [bool])
    assert f(True) == 12
    assert f(False) == 13

def test_int_ops():
    def ops(i):
        x = 0
        x += i < i
        x += i <= i
        x += i == i
        x += i != i
        x += i >= i
        x += i > i
        #x += i is not None
        #x += i is None
        return i + 1 * i // i - 1
    f = compile_function(ops, [int])
    assert f(1) == 1
    assert f(2) == 2

def test_function_call():
    def callee():
        return 1
    def caller():
        return 3 + callee()
    f = compile_function(caller, [])
    assert f() == 4

def test_recursive_call():
    def call_ackermann(n, m):
        return ackermann(n, m)
    def ackermann(n, m):
        if n == 0:
            return m + 1
        if m == 0:
            return ackermann(n - 1, 1)
        return ackermann(n - 1, ackermann(n, m - 1))
    f = compile_function(call_ackermann, [int, int])
    assert f(0, 2) == 3
    
def XXXtest_tuple_getitem(): 
    def list_getitem(i): 
        l = (1,2,i)
        return l[1]
    f = compile_function(list_getitem, [int])
    assert f(1) == 2 

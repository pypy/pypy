from __future__ import division

import sys
import py

from pypy.translator.translator import Translator
from pypy.translator.llvm2.genllvm import genllvm
from pypy.translator.llvm2.test import llvmsnippet
from pypy.objspace.flow.model import Constant, Variable

from pypy.rpython.rtyper import RPythonTyper

py.log.setconsumer("genllvm", py.log.STDOUT)

## def setup_module(mod):
##     mod.llvm_found = is_on_path("llvm-as")

def compile_function(function, annotate):
    t = Translator(function)
    a = t.annotate(annotate)
    rt = RPythonTyper(a)
    rt.specialize()
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
        return i + 1 * i // i - 1
    f = compile_function(ops, [int])
    assert f(1) == 1
    assert f(2) == 2
    

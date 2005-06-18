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

def test_genllvm():
    f = compile_function(llvmsnippet.simple1, [])
    assert f() == 1

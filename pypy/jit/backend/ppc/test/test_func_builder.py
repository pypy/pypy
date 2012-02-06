import py
import random, sys, os

from pypy.jit.backend.ppc.ppc_assembler import MyPPCAssembler
from pypy.jit.backend.ppc.symbol_lookup import lookup
from pypy.jit.backend.ppc.func_builder import make_func
from pypy.jit.backend.ppc import form, func_builder
from pypy.jit.backend.ppc.regname import *
from pypy.jit.backend.detect_cpu import autodetect_main_model

class TestFuncBuilderTest(object):
    def setup_class(cls):
        if autodetect_main_model() not in ["ppc", "ppc64"]: 
            py.test.skip("can't test all of ppcgen on non-PPC!")

    def test_simple(self):
        a = MyPPCAssembler()
        a.blr()
        f = make_func(a, "O", "O")
        assert f(1) == 1
        raises(TypeError, f)
        raises(TypeError, f, 1, 2)

    def test_less_simple(self):
        a = MyPPCAssembler()
        s = lookup("PyNumber_Add")
        a.load_word(r5, s)
        a.mtctr(r5)
        a.bctr()
        f = make_func(a, "O", "OO")
        raises(TypeError, f)
        raises(TypeError, f, 1)
        assert f(1, 2) == 3
        raises(TypeError, f, 1, 2, 3)

    def test_signature(self):
        a = MyPPCAssembler()
        a.add(r3, r3, r4)
        a.blr()
        f = make_func(a, "i", "ii")
        raises(TypeError, f)
        raises(TypeError, f, 1)
        assert f(1, 2) == 3
        raises(TypeError, f, 1, 2, 3)
        raises(TypeError, f, 1, "2")

    def test_signature2(self):
        a = MyPPCAssembler()
        a.add(r3, r3, r4)
        a.add(r3, r3, r5)
        a.add(r3, r3, r6)
        a.add(r3, r3, r7)
        s = lookup("PyInt_FromLong")
        a.load_word(r0, s)
        a.mtctr(r0)
        a.bctr()
        f = make_func(a, "O", "iiiii")
        raises(TypeError, f)
        raises(TypeError, f, 1)
        assert f(1, 2, 3, 4, 5) == 1 + 2 + 3 + 4 + 5
        raises(TypeError, f, 1, 2, 3)
        raises(TypeError, f, 1, "2", 3, 4, 5)

    def test_floats(self):
        a = MyPPCAssembler()
        a.fadd(fr1, fr1, fr2)
        a.blr()
        f = make_func(a, 'f', 'ff')
        raises(TypeError, f)
        raises(TypeError, f, 1.0)
        assert f(1.0, 2.0) == 3.0
        raises(TypeError, f, 1.0, 2.0, 3.0)
        raises(TypeError, f, 1.0, 2)

    def test_fast_entry(self):
        a = MyPPCAssembler()
        a.blr()
        f = make_func(a, "O", "O")
        assert f(1) == 1
        b = MyPPCAssembler()
        from pypy.jit.backend.ppc.ppcgen import util
        # eurgh!:
        b.load_word(r0, util.access_at(id(f.code), 8) + f.FAST_ENTRY_LABEL)
        b.mtctr(r0)
        b.bctr()
        g = make_func(b, "O", "O")
        assert g(1) == 1

import py
import random, sys, os

from pypy.jit.codegen.ppc.ppcgen.ppc_assembler import BasicPPCAssembler, MyPPCAssembler
from pypy.jit.codegen.ppc.ppcgen.symbol_lookup import lookup
from pypy.jit.codegen.ppc.ppcgen.regname import *
from pypy.jit.codegen.ppc.ppcgen import form, pystructs


class TestDisassemble(object):
    def test_match(self):
        A = BasicPPCAssembler
        a = A()
        a.add(1, 2, 3)
        inst = a.insts[-1]
        assert A.add.match(inst.assemble())


class TestAssemble(object):
        
    def setup_class(cls):
        if (not hasattr(os, 'uname') or
            os.uname()[-1] != 'Power Macintosh'):
            py.test.skip("can't test all of ppcgen on non-PPC!")

    def test_tuplelength(self):
        a = MyPPCAssembler()

        a.lwz(3, 4, pystructs.PyVarObject.ob_size)
        a.load_word(5, lookup("PyInt_FromLong"))
        a.mtctr(5)
        a.bctr()

        f = a.assemble()
        assert f() == 0
        assert f(1) == 1
        assert f('') == 1


    def test_tuplelength2(self):
        a = MyPPCAssembler()

        a.mflr(0)
        a.stw(0, 1, 8)
        a.stwu(1, 1, -80)
        a.mr(3, 4)
        a.load_word(5, lookup("PyTuple_Size"))
        a.mtctr(5)
        a.bctrl()
        a.load_word(5, lookup("PyInt_FromLong"))
        a.mtctr(5)
        a.bctrl()
        a.lwz(0, 1, 88)
        a.addi(1, 1, 80)
        a.mtlr(0)
        a.blr()

        f = a.assemble()
        assert f() == 0
        assert f(1) == 1
        assert f('') == 1
        assert f('', 3) == 2


    def test_intcheck(self):
        a = MyPPCAssembler()

        a.lwz(r5, r4, pystructs.PyVarObject.ob_size)
        a.cmpwi(r5, 1)
        a.bne("not_one")
        a.lwz(r5, r4, pystructs.PyTupleObject.ob_item + 0*4)
        a.lwz(r5, r5, 4)
        a.load_word(r6, lookup("PyInt_Type"))
        a.cmpw(r5, r6)
        a.bne("not_int")
        a.li(r3, 1)
        a.b("exit")
        a.label("not_int")
        a.li(r3, 0)
        a.b("exit")
        a.label("not_one")
        a.li(r3, 2)
        a.label("exit")
        a.load_word(r5, lookup("PyInt_FromLong"))
        a.mtctr(r5)
        a.bctr()

        f = a.assemble()

        assert f() == 2
        assert f("", "") == 2
        assert f("") == 0
        assert f(1) == 1


    def test_raise(self):
        a = MyPPCAssembler()

        a.mflr(0)
        a.stw(0, 1, 8)
        a.stwu(1, 1, -80)

        err_set = lookup("PyErr_SetObject")
        exc = lookup("PyExc_ValueError")

        a.load_word(5, err_set)
        a.mtctr(5)
        a.load_from(3, exc)
        a.mr(4, 3)
        a.bctrl()

        a.li(3, 0)

        a.lwz(0, 1, 88)
        a.addi(1, 1, 80)
        a.mtlr(0)
        a.blr()

        raises(ValueError, a.assemble())


    def test_makestring(self):
        a = MyPPCAssembler()

        a.li(r3, 0)
        a.li(r4, 0)
        a.load_word(r5, lookup("PyString_FromStringAndSize"))
        a.mtctr(r5)
        a.bctr()

        f = a.assemble()
        assert f() == ''


    def test_numberadd(self):
        a = MyPPCAssembler()

        a.lwz(r5, r4, pystructs.PyVarObject.ob_size)
        a.cmpwi(r5, 2)
        a.bne("err_out")

        a.lwz(r3, r4, 12)
        a.lwz(r4, r4, 16)

        a.load_word(r5, lookup("PyNumber_Add"))
        a.mtctr(r5)
        a.bctr()

        a.label("err_out")

        a.mflr(r0)
        a.stw(r0, r1, 8)
        a.stwu(r1, r1, -80)

        err_set = lookup("PyErr_SetObject")
        exc = lookup("PyExc_TypeError")

        a.load_word(r5, err_set)
        a.mtctr(r5)
        a.load_from(r3, exc)
        a.mr(r4, r3)
        a.bctrl()

        a.li(r3, 0)

        a.lwz(r0, r1, 88)
        a.addi(r1, r1, 80)
        a.mtlr(r0)
        a.blr()

        f = a.assemble()

        raises(TypeError, f)
        raises(TypeError, f, '', 1)
        raises(TypeError, f, 1)
        raises(TypeError, f, 1, 2, 3)
        assert f(1, 2) == 3
        assert f('a', 'b') == 'ab'


    def test_assemblerChecks(self):
        def testFailure(idesc, *args):
            a = MyPPCAssembler()
            raises(ValueError, idesc.__get__(a), *args)
        def testSucceed(idesc, *args):
            a = MyPPCAssembler()
            # "assertNotRaises" :-)
            idesc.__get__(a)(*args)
        testFailure(MyPPCAssembler.add, 32, 31, 30)
        testFailure(MyPPCAssembler.add, -1, 31, 30)
        testSucceed(MyPPCAssembler.bne, -12)
        testSucceed(MyPPCAssembler.lwz, 0, 0, 32767)
        testSucceed(MyPPCAssembler.lwz, 0, 0, -32768)

import py
import random, sys, os

from pypy.jit.backend.ppc.codebuilder import BasicPPCAssembler, PPCBuilder
from pypy.jit.backend.ppc.symbol_lookup import lookup
from pypy.jit.backend.ppc.regname import *
from pypy.jit.backend.ppc.register import *
from pypy.jit.backend.ppc import form
from pypy.jit.backend.detect_cpu import autodetect_main_model
from pypy.jit.backend.ppc.arch import IS_PPC_32, IS_PPC_64, WORD

from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rpython.annlowlevel import llhelper

class TestDisassemble(object):
    def test_match(self):
        A = BasicPPCAssembler
        a = A()
        a.add(1, 2, 3)
        inst = a.insts[-1]
        assert A.add.match(inst.assemble())


"""
Creates the boilerplate code for the tests.
- Make a PPCBuilder object
- Let the given test create the machine code
- Create a function and call it
- Compare the return value with the expected result
"""
def asmtest(expected=-1):
    def testmaker(test):
        def newtest(self):
            a = PPCBuilder()
            test(self, a)
            f = a.assemble()
            assert f() == expected
        return newtest
    return testmaker


"""
Treats the given bitstring as binary representation
of an integer in two's complement.
"""
def bits_to_signed_int(bits):
    assert len(bits) > 0
    sign = 1
    if bits[0] == "1":
        sign = -1
    bits = bits[1:].replace("0", "$").replace("1", "0").replace("$", "1")
    return sign * (int(bits, 2) + 1)

def hex_to_signed_int(hx):
    return bits_to_signed_int(bin(int(hx, 16))[2:])

# Testing simple assembler instructions
class TestAssemble(object):
    def setup_class(cls):
        if autodetect_main_model() not in ["ppc", "ppc64"]: 
            py.test.skip("can't test all of ppcgen on non-PPC!")
        py.test.xfail("assemble does not return a function any longer, fix tests")

    """
    Tests are build like this:

        @asmtest(expected=<EXPECTED RESULT>)
        def testX(self, assembler):
            <Assembler Code>


    This is equivalent to:


        def testX(self):
            assembler = MyPPCAssembler()

            <Assembler Code>

            f = assembler.assemble()
            assert f() == <EXPECTED RESULT>
    """

    @asmtest(expected=200)
    def test_li(self, a):
        a.li(3, 200)
        a.blr()

    @asmtest(expected=7)
    def test_add_imm(self, a):
        a.li(3, 6)
        a.addi(3, 3, 1)
        a.blr()

    @asmtest(expected=12341234)
    def test_load_imm(self, a):
        a.load_imm(r10, 12341234)
        a.mtctr(10)
        a.mfctr(11)
        a.mr(3, 11)
        a.blr()

    @asmtest(expected=33333333)
    def test_add_reg(self, a):
        a.load_imm(r10, 11111111)
        a.load_imm(r11, 22222222)
        a.add(12, 10, 11)
        a.mr(3, 12)
        a.blr()

    @asmtest(expected=-1000)
    def test_add_pos_and_neg(self, a):
        a.load_imm(r10, 2000)
        a.load_imm(r11, -3000)
        a.add(3, 10, 11)
        a.blr()

    @asmtest(expected=7)
    def test_sub_imm(self, a):
        a.li(3, 10)
        a.subi(3, 3, 3)
        a.blr()

    @asmtest(expected=(123435 - 76457))
    def test_sub_reg(self, a):
        a.load_imm(r5, 123435)
        a.load_imm(r6, 76457)
        a.sub(3, 5, 6)
        a.blr()

    @asmtest(expected=(10000 * 5000))
    def test_mul_imm(self, a):
        a.load_imm(r3, 10000)
        a.mulli(3, 3, 5000)
        a.blr()

    # 1000000 * 1000000 = 0b1110100011010100101001010001000000000000
    # expect: r3        =   -HWORD-|11010100101001010001000000000000
    @asmtest(expected=bits_to_signed_int('11010100101001010001000000000000'))
    def test_mullw(self, a):
        word = 1000000
        a.load_imm(r5, word)
        a.load_imm(r6, word)
        a.mullw(3, 5, 6)
        if IS_PPC_64:
            a.extsw(3, 3)
        a.blr()

    # 1000000 * 1000000 = 0b1110100011010100101001010001000000000000
    # expect: r3        =   11101000|------------LWORD--------------
    @asmtest(expected=int('11101000', 2))
    def test_mulhw(self, a):
        word = 1000000
        a.load_imm(r5, word)
        a.load_imm(r6, word)
        a.mulhw(3, 5, 6)
        if IS_PPC_64:
            a.extsw(3, 3)
        a.blr()

    # 1000000 * 1000000 = 0b1110100011010100101001010001000000000000
    # expect: r3        =   11101000|------------LWORD--------------
    @asmtest(expected=int('11101000', 2))
    def test_mulhwu(self, a):
        word = 1000000
        a.load_imm(r5, word)
        a.load_imm(r6, word)
        a.mulhwu(3, 5, 6)
        if IS_PPC_64:
            a.extsw(3, 3)
        a.blr()

    @asmtest(expected=10000)
    def test_divw(self, a):
        divident = 1000000
        divisor = 100
        a.load_imm(r10, divident)
        a.load_imm(r11, divisor)
        a.divw(3, 10, 11)
        a.blr()

    def test_call_function(self):
        functype =  lltype.Ptr(lltype.FuncType([lltype.Signed], lltype.Signed))
        call_addr = rffi.cast(lltype.Signed, llhelper(functype, func))
        a = PPCBuilder()

        # NOW EXPLICITLY:
        # 
        # - Load the address of the function to call into a register x
        # - Move the content of this register x into CTR
        # - Set the LR manually (or with bctrl)
        # - Do jump

        a.li(3, 50)
        if IS_PPC_32:
            a.load_imm(r10, call_addr)
        else:
            a.load_from_addr(r10, call_addr)
            a.load_from_addr(r2, call_addr+WORD)
            a.load_from_addr(r11, call_addr+2*WORD)
        a.mtctr(10)
        a.bctr()
        a.blr()

        f = a.assemble()
        assert f() == 65

    @asmtest(expected=0)
    def test_and(self, a):
        a.load_imm(r10, 8)
        a.load_imm(r11, 7)
        a.and_(3, 10, 11)
        a.blr()

    @asmtest(expected=15)
    def test_or(self, a):
        a.load_imm(r10, 8)
        a.load_imm(r11, 7)
        a.or_(3, 10, 11)
        a.blr()

    @asmtest(expected=15)
    def test_nand(self, a):
        a.load_imm(r10, 8)
        a.load_imm(r11, 7)
        a.nand(3, 10, 11)
        a.load_imm(r12, 0x0000000F) # zero out first 28 bits
        a.and_(3, 3, 12)            # 
        a.blr()

    @asmtest(expected=1)
    def test_nor(self, a):
        a.load_imm(r10, 10)
        a.load_imm(r11, 6)
        a.nor(3, 10, 11)
        a.load_imm(r12, 0x0000000F) # zero out first 28 bits
        a.and_(3, 3, 12)            # 
        a.blr()

    @asmtest(expected=5)
    def test_xor(self, a):
        a.load_imm(r10, 15)
        a.load_imm(r11, 10)
        a.xor(3, 10, 11)
        a.blr()

    @asmtest(expected=0x120)
    def test_slw(self, a):
        a.load_imm(r10, 9)
        a.load_imm(r11, 5)
        a.slw(3, 10, 11)
        a.blr()

    @asmtest(expected=9)
    def test_srw(self, a):
        a.load_imm(r10, 0x120)
        a.load_imm(r11, 5)
        a.srw(3, 10, 11)
        a.blr()

    def test_neg(self):
        a = PPCBuilder()
        a.load_imm(r10, 0x0000F0F0)
        a.neg(3, 10)
        a.blr()
        f = a.assemble()
        assert f() == hex_to_signed_int("FFFF0F10")

    def test_load_and_store(self):
        a = PPCBuilder()
        word1 = 1000
        word2 = 2000
        p = lltype.malloc(rffi.CArray(lltype.Signed), 2, flavor="raw")

        a.load_imm(r10, word1)
        a.load_imm(r11, word2)

        a.load_imm(r8, rffi.cast(lltype.Signed, p))
        a.load_imm(r9, rffi.cast(lltype.Signed, p) + WORD)

        a.stw(10, 8, 0)
        a.stw(11, 9, 0)
        a.lwz(4, 8, 0)
        a.lwz(5, 9, 0)
        a.add(3, 4, 5)
        a.blr()
        f = a.assemble()
        assert f() == word1 + word2
        lltype.free(p, flavor="raw")

    def test_load_from(self):
        a = PPCBuilder()
        
        p = lltype.malloc(rffi.CArray(rffi.LONG), 1, flavor="raw")
        addr = rffi.cast(lltype.Signed, p)
        p[0] = rffi.cast(rffi.LONG, 200)

        a.load_from_addr(r3, addr)
        a.blr()
        f = a.assemble()
        assert f() == 200
        p[0] = rffi.cast(rffi.LONG, 300)
        assert f() == 300
        lltype.free(p, flavor="raw")


class AsmCode(object):
    def __init__(self, size):
        self.code = MachineCodeBlockWrapper()

    def emit(self, insn):
        bytes = struct.pack("i", insn)
        for byte in bytes:
            self.code.writechar(byte)

    def get_function(self):
        i = self.code.materialize(AsmMemoryManager(), [])
        t = lltype.FuncType([], lltype.Signed)
        return rffi.cast(lltype.Ptr(t), i)


def func(arg):
    return arg + 15

def is_64_bit_arch():
    import sys
    return sys.maxint == 9223372036854775807

"""
class TestAssemble(object):
        
    def setup_class(cls):
        #if (not hasattr(os, 'uname') or
        if autodetect_main_model() not in ["ppc", "ppc64"]: 
            #os.uname()[-1] in ['Power Macintosh', 'PPC64']:
            
            py.test.skip("can't test all of ppcgen on non-PPC!")

    def test_tuplelength(self):
        a = MyPPCAssembler()

        a.lwz(3, 4, pystructs.PyVarObject.ob_size)
        a.load_imm(5, lookup("PyInt_FromLong"))
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
        a.load_imm(5, lookup("PyTuple_Size"))
        a.mtctr(5)
        a.bctrl()
        a.load_imm(5, lookup("PyInt_FromLong"))
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
        a.load_imm(r6, lookup("PyInt_Type"))
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
        a.load_imm(r5, lookup("PyInt_FromLong"))
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

        a.load_imm(5, err_set)
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
        a.load_imm(r5, lookup("PyString_FromStringAndSize"))
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

        a.load_imm(r5, lookup("PyNumber_Add"))
        a.mtctr(r5)
        a.bctr()

        a.label("err_out")

        a.mflr(r0)
        a.stw(r0, r1, 8)
        a.stwu(r1, r1, -80)

        err_set = lookup("PyErr_SetObject")
        exc = lookup("PyExc_TypeError")

        a.load_imm(r5, err_set)
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
"""

from pypy.jit.backend.x86.regloc import *
from pypy.jit.backend.x86.assembler import Assembler386
from pypy.jit.backend.x86.regalloc import X86FrameManager, get_ebp_ofs
from pypy.jit.metainterp.history import BoxInt, BoxPtr, BoxFloat, ConstFloat
from pypy.jit.metainterp.history import INT, REF, FLOAT
from pypy.rlib.rarithmetic import intmask
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.jit.backend.x86.arch import WORD, IS_X86_32, IS_X86_64
from pypy.jit.backend.detect_cpu import getcpuclass 
from pypy.jit.backend.x86.regalloc import X86RegisterManager, X86_64_RegisterManager, X86XMMRegisterManager, X86_64_XMMRegisterManager
from pypy.jit.backend.llsupport import jitframe
from pypy.jit.codewriter import longlong
import ctypes
import py

ACTUAL_CPU = getcpuclass()
if not hasattr(ACTUAL_CPU, 'NUM_REGS'):
    py.test.skip('unsupported CPU')

class FakeCPU:
    rtyper = None
    supports_floats = True
    NUM_REGS = ACTUAL_CPU.NUM_REGS

    class gc_ll_descr:
        kind = "boehm"

    def fielddescrof(self, STRUCT, name):
        return 42

    def get_fail_descr_from_number(self, num):
        assert num == 0x1C3
        return FakeFailDescr()

    def get_failargs_limit(self):
        return 1000

class FakeMC:
    def __init__(self):
        self.content = []
    def writechar(self, char):
        self.content.append(ord(char))

class FakeFailDescr:
    def hide(self, cpu):
        return rffi.cast(llmemory.GCREF, 123)

# ____________________________________________________________

class TestRegallocPushPop(object):

    def do_test(self, callback):
        from pypy.jit.backend.x86.regalloc import X86FrameManager
        from pypy.jit.backend.x86.regalloc import X86XMMRegisterManager
        class FakeToken:
            class compiled_loop_token:
                asmmemmgr_blocks = None
        cpu = ACTUAL_CPU(None, None)
        cpu.setup()
        looptoken = FakeToken()
        asm = cpu.assembler
        asm.setup_once()
        asm.setup(looptoken)
        self.fm = X86FrameManager()
        self.xrm = X86XMMRegisterManager(None, frame_manager=self.fm,
                                         assembler=asm)
        callback(asm)
        asm.mc.RET()
        rawstart = asm.materialize_loop(looptoken)
        #
        F = ctypes.CFUNCTYPE(ctypes.c_long)
        fn = ctypes.cast(rawstart, F)
        res = fn()
        return res

    def test_simple(self):
        def callback(asm):
            asm.mov(imm(42), edx)
            asm.regalloc_push(edx)
            asm.regalloc_pop(eax)
        res = self.do_test(callback)
        assert res == 42

    def test_push_stack(self):
        def callback(asm):
            loc = self.fm.frame_pos(5, INT)
            asm.mc.SUB_ri(esp.value, 64)
            asm.mov(imm(42), loc)
            asm.regalloc_push(loc)
            asm.regalloc_pop(eax)
            asm.mc.ADD_ri(esp.value, 64)
        res = self.do_test(callback)
        assert res == 42

    def test_pop_stack(self):
        def callback(asm):
            loc = self.fm.frame_pos(5, INT)
            asm.mc.SUB_ri(esp.value, 64)
            asm.mov(imm(42), edx)
            asm.regalloc_push(edx)
            asm.regalloc_pop(loc)
            asm.mov(loc, eax)
            asm.mc.ADD_ri(esp.value, 64)
        res = self.do_test(callback)
        assert res == 42

    def test_simple_xmm(self):
        def callback(asm):
            c = ConstFloat(longlong.getfloatstorage(-42.5))
            loc = self.xrm.convert_to_imm(c)
            asm.mov(loc, xmm5)
            asm.regalloc_push(xmm5)
            asm.regalloc_pop(xmm0)
            asm.mc.CVTTSD2SI(eax, xmm0)
        res = self.do_test(callback)
        assert res == -42

    def test_push_stack_xmm(self):
        def callback(asm):
            c = ConstFloat(longlong.getfloatstorage(-42.5))
            loc = self.xrm.convert_to_imm(c)
            loc2 = self.fm.frame_pos(4, FLOAT)
            asm.mc.SUB_ri(esp.value, 64)
            asm.mov(loc, xmm5)
            asm.mov(xmm5, loc2)
            asm.regalloc_push(loc2)
            asm.regalloc_pop(xmm0)
            asm.mc.ADD_ri(esp.value, 64)
            asm.mc.CVTTSD2SI(eax, xmm0)
        res = self.do_test(callback)
        assert res == -42

    def test_pop_stack_xmm(self):
        def callback(asm):
            c = ConstFloat(longlong.getfloatstorage(-42.5))
            loc = self.xrm.convert_to_imm(c)
            loc2 = self.fm.frame_pos(4, FLOAT)
            asm.mc.SUB_ri(esp.value, 64)
            asm.mov(loc, xmm5)
            asm.regalloc_push(xmm5)
            asm.regalloc_pop(loc2)
            asm.mov(loc2, xmm0)
            asm.mc.ADD_ri(esp.value, 64)
            asm.mc.CVTTSD2SI(eax, xmm0)
        res = self.do_test(callback)
        assert res == -42

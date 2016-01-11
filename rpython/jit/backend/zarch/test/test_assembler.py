import py
import struct
import math
from rpython.jit.backend.zarch import conditions as con
from rpython.jit.backend.zarch import masks as msk
from rpython.jit.backend.zarch import registers as reg
from rpython.jit.backend.zarch.assembler import AssemblerZARCH
from rpython.jit.backend.zarch import locations as loc
from rpython.jit.backend.zarch.test.support import run_asm
from rpython.jit.backend.detect_cpu import getcpuclass
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.codewriter import longlong

from rpython.rtyper.annlowlevel import llhelper
from rpython.rtyper.lltypesystem import lltype, rffi, ll2ctypes
from rpython.jit.metainterp.history import JitCellToken
from rpython.jit.backend.model import CompiledLoopToken
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rtyper.annlowlevel import llhelper
from rpython.rlib.objectmodel import specialize
from rpython.rlib.debug import ll_assert
from rpython.rlib.longlong2float import (float2longlong,
        DOUBLE_ARRAY_PTR, singlefloat2uint_emulator)
import ctypes

CPU = getcpuclass()

def BFL(value, short=False):
    if short:
        return struct.pack('f', value)
    return struct.pack('>q', float2longlong(value))

def ADDR(value):
    ptr = ll2ctypes.lltype2ctypes(value)
    addr = ctypes.addressof(ptr.contents.items)
    return struct.pack('>Q', addr)

def gen_func_prolog(mc):
    STACK_FRAME_SIZE = 40
    mc.STMG(r.r11, r.r15, l.addr(-STACK_FRAME_SIZE, r.SP))
    mc.AHI(r.SP, l.imm(-STACK_FRAME_SIZE))

def gen_func_epilog(mc):
    mc.LMG(r.r11, r.r15, l.addr(0, r.SP))
    mc.BCR_rr(0xf, r.r14.value) # jmp to

def isclose(a,b, rel_tol=1e-9, abs_tol=0.0):
    if math.isnan(a) and math.isnan(b):
        return True
    if a == b:
        return True
    # from PEP 485, added in python 3.5
    return abs(a-b) <= max( rel_tol * max(abs(a), abs(b)), abs_tol )

class LiteralPoolCtx(object):
    def __init__(self, asm):
        self.asm = asm
        self.lit_label = LabelCtx(asm, 'lit')

    def __enter__(self):
        self.lit_label.__enter__()
        self.asm.mc.BRAS(reg.r13, loc.imm(0))
        return self

    def __exit__(self, a, b, c):
        self.lit_label.__exit__(None, None, None)
        self.asm.jump_here(self.asm.mc.BRAS, 'lit')

    def addr(self, mem):
        self.asm.mc.write(ADDR(mem))

    def float(self, val):
        self.asm.mc.write(BFL(val))

    def single_float(self, val):
        self.asm.mc.write(BFL(val, short=True))

    def int64(self, val):
        self.asm.mc.write(struct.pack('>q', val))

class LabelCtx(object):
    def __init__(self, asm, name):
        self.asm = asm
        self.name = name
    def __enter__(self):
        self.asm.mc.mark_op(self.name)
        return self
    def __exit__(self, a, b, c):
        self.asm.mc.mark_op(self.name + '.end')

class ActivationRecordCtx(object):
    def __init__(self, asm, name='func'):
        self.asm = asm
        self.name = name
        self.asm.mc.mark_op(self.name)
    def __enter__(self):
        gen_func_prolog(self.asm.mc)
        return self
    def __exit__(self, a, b, c):
        gen_func_epilog(self.asm.a.mc)
        self.asm.mc.mark_op(self.name + '.end')


class TestRunningAssembler(object):
    def setup_method(self, method):
        cpu = CPU(None, None)
        self.a = AssemblerZARCH(cpu)
        self.a.setup_once()
        token = JitCellToken()
        clt = CompiledLoopToken(cpu, 0)
        clt.allgcrefs = []
        token.compiled_loop_token = clt
        self.a.setup(token)
        self.mc = self.a.mc

    def test_make_operation_list(self):
        i = rop.INT_ADD
        from rpython.jit.backend.zarch import assembler
        assert assembler.asm_operations[i] \
            is AssemblerZARCH.emit_int_add.im_func

    def test_byte_count_instr(self):
        assert self.mc.BRC_byte_count == 4
        assert self.mc.LG_byte_count == 6

    def test_load_small_int_to_reg(self):
        self.a.mc.LGHI(reg.r2, loc.imm(123))
        self.a.jmpto(reg.r14)
        assert run_asm(self.a) == 123

    def test_prolog_epilog(self):
        gen_func_prolog(self.a.mc)
        self.a.mc.LGHI(reg.r2, loc.imm(123))
        gen_func_epilog(self.a.mc)
        assert run_asm(self.a) == 123

    def test_simple_func(self):
        # enter
        self.a.mc.STMG(reg.r11, reg.r15, loc.addr(-96, reg.SP))
        self.a.mc.AHI(reg.SP, loc.imm(-96))
        # from the start of BRASL to end of jmpto there are 8+6 bytes
        self.a.mc.BRASL(reg.r14, loc.imm(8+6))
        self.a.mc.LMG(reg.r11, reg.r15, loc.addr(0, reg.SP))
        self.a.jmpto(reg.r14)

        addr = self.a.mc.get_relative_pos()
        assert addr & 0x1 == 0
        gen_func_prolog(self.a.mc)
        self.a.mc.LGHI(reg.r2, loc.imm(321))
        gen_func_epilog(self.a.mc)
        assert run_asm(self.a) == 321

    def test_simple_loop(self):
        self.a.mc.LGHI(reg.r3, loc.imm(2**15-1))
        self.a.mc.LGHI(reg.r4, loc.imm(1))
        L1 = self.a.mc.get_relative_pos()
        self.a.mc.SGR(reg.r3, reg.r4)
        LJ = self.a.mc.get_relative_pos()
        self.a.mc.BRCL(con.GT, loc.imm(L1-LJ))
        self.a.mc.LGR(reg.r2, reg.r3)
        self.a.jmpto(reg.r14)
        assert run_asm(self.a) == 0

    def test_and_imm(self):
        self.a.mc.NIHH(reg.r2, loc.imm(0))
        self.a.mc.NIHL(reg.r2, loc.imm(0))
        self.a.mc.NILL(reg.r2, loc.imm(0))
        self.a.mc.NILH(reg.r2, loc.imm(0))
        self.a.jmpto(reg.r14)
        assert run_asm(self.a) == 0

    def test_or_imm(self):
        self.a.mc.OIHH(reg.r2, loc.imm(0xffff))
        self.a.mc.OIHL(reg.r2, loc.imm(0xffff))
        self.a.mc.OILL(reg.r2, loc.imm(0xffff))
        self.a.mc.OILH(reg.r2, loc.imm(0xffff))
        self.a.jmpto(reg.r14)
        assert run_asm(self.a) == -1

    def test_xor(self):
        self.a.mc.XGR(reg.r2, reg.r2)
        self.a.jmpto(reg.r14)
        assert run_asm(self.a) == 0

    def test_literal_pool(self):
        gen_func_prolog(self.a.mc)
        self.a.mc.BRAS(reg.r13, loc.imm(8 + self.mc.BRAS_byte_count))
        self.a.mc.write('\x08\x07\x06\x05\x04\x03\x02\x01')
        self.a.mc.LG(reg.r2, loc.addr(0, reg.r13))
        gen_func_epilog(self.a.mc)
        assert run_asm(self.a) == 0x0807060504030201

    def label(self, name, func=False):
        if not func:
            return LabelCtx(self, name)
        return ActivationRecordCtx(self, name)

    def patch_branch_imm16(self, base, imm):
        imm = (imm & 0xffff) >> 1
        self.mc.overwrite(base, chr((imm >> 8) & 0xFF))
        self.mc.overwrite(base+1, chr(imm & 0xFF))

    def pos(self, name):
        return self.mc.ops_offset[name]
    def cur(self):
        return self.mc.get_relative_pos()

    def jump_here(self, func, name):
        if func.__name__ == 'BRAS':
            self.patch_branch_imm16(self.pos(name)+2, self.cur() - self.pos(name))
        else:
            raise NotImplementedError

    def jump_to(self, reg, label):
        val = (self.pos(label) - self.cur())
        self.mc.BRAS(reg, loc.imm(val))

    def test_stmg(self):
        self.mc.LGR(reg.r2, reg.r15)
        self.a.jmpto(reg.r14)
        print hex(run_asm(self.a))

    def test_recursion(self):
        with ActivationRecordCtx(self):
            with self.label('lit'):
                self.mc.BRAS(reg.r13, loc.imm(0))
            self.mc.write('\x00\x00\x00\x00\x00\x00\x00\x00')
            self.jump_here(self.mc.BRAS, 'lit')
            # recurse X times
            self.mc.XGR(reg.r2, reg.r2)
            self.mc.LGHI(reg.r9, loc.imm(15))
            with self.label('L1'):
                self.mc.BRAS(reg.r14, loc.imm(0))
            with ActivationRecordCtx(self, 'rec'):
                self.mc.AGR(reg.r2, reg.r9)
                self.mc.AHI(reg.r9, loc.imm(-1))
                # if not entered recursion, return from activation record
                # implicitly generated here by with statement
                self.mc.BRC(con.GT, loc.imm(self.pos('rec') - self.cur()))
            self.jump_here(self.mc.BRAS, 'L1')
            # call rec... recursivly
            self.jump_to(reg.r14, 'rec')
        self.a.jmpto(reg.r14)
        assert run_asm(self.a) == 120

    def test_printf(self):
        with ActivationRecordCtx(self):
            with self.label('lit'):
                self.mc.BRAS(reg.r13, loc.imm(0))
            for c in "hello syscall\n":
                self.mc.writechar(c)
            self.jump_here(self.mc.BRAS, 'lit')
            self.mc.LGHI(reg.r2, loc.imm(1)) # stderr
            self.mc.LA(reg.r3, loc.addr(0, reg.r13)) # char*
            self.mc.LGHI(reg.r4, loc.imm(14)) # length
            # write sys call
            self.mc.SVC(loc.imm(4))
        self.a.jmpto(reg.r14)
        assert run_asm(self.a) == 14

    def test_float(self):
        with ActivationRecordCtx(self):
            with self.label('lit'):
                self.mc.BRAS(reg.r13, loc.imm(0))
            self.mc.write(BFL(-15.0))
            self.jump_here(self.mc.BRAS, 'lit')
            self.mc.LD(reg.f0, loc.addr(0, reg.r13))
            self.mc.CGDBR(reg.r2, msk.RND_CURMODE, reg.f0)
        self.a.jmpto(reg.r14)
        assert run_asm(self.a) == -15

    @py.test.mark.parametrize("v1,v2,res", [
        (    0.0,       0.0,       0.0),
        (   -15.0,    -15.0,     -30.0),
        (    1.5,     -3.22,      -1.72),
        (    0.5,       0.0,       0.5),
        (    0.0001,   -0.0002,   -0.0001),
        (float('nan'), 1.0, float('nan')),
    ])
    def test_float_to_memory(self, v1, v2, res):
        with lltype.scoped_alloc(DOUBLE_ARRAY_PTR.TO, 16) as mem:
            with ActivationRecordCtx(self):
                with self.label('lit'):
                    self.mc.BRAS(reg.r13, loc.imm(0))
                self.mc.write(BFL(v1))
                self.mc.write(BFL(v2))
                self.mc.write(ADDR(mem))
                self.jump_here(self.mc.BRAS, 'lit')
                self.mc.LD(reg.f0, loc.addr(0, reg.r13))
                self.mc.LD(reg.f1, loc.addr(8, reg.r13))
                self.mc.ADBR(reg.f0, reg.f1)
                self.mc.LG(reg.r11, loc.addr(16, reg.r13))
                self.mc.STD(reg.f0, loc.addr(0, reg.r11))
            self.a.jmpto(reg.r14)
            run_asm(self.a)
            assert isclose(mem[0],res)

    @py.test.mark.parametrize("v1,v2,res", [
        (    0.0,       0.0,       0.0),
        (   -15.0,    -15.0,     225.0),
        (    0.0, 9876543.21,      0.0),
        (   -0.5,      14.5,      -7.25),
        (    0.0001,    2.0,       0.0002),
        (float('nan'), 1.0, float('nan')),
    ])
    def test_float_mul_to_memory(self, v1, v2, res):
        with lltype.scoped_alloc(DOUBLE_ARRAY_PTR.TO, 16) as mem:
            with ActivationRecordCtx(self):
                with LiteralPoolCtx(self) as pool:
                    pool.float(v1)
                    pool.float(v2)
                    pool.addr(mem)
                self.mc.LD(reg.f0, loc.addr(0, reg.r13))
                self.mc.MDB(reg.f0, loc.addr(8, reg.r13))
                self.mc.LG(reg.r11, loc.addr(16, reg.r13))
                self.mc.STD(reg.f0, loc.addr(0, reg.r11))
            self.a.jmpto(reg.r14)
            run_asm(self.a)
            assert isclose(mem[0],res)

    def test_float_load_zero(self):
        with lltype.scoped_alloc(DOUBLE_ARRAY_PTR.TO, 16) as mem:
            with ActivationRecordCtx(self):
                with LiteralPoolCtx(self) as pool:
                    pool.addr(mem)
                self.mc.LZDR(reg.f0)
                self.mc.LG(reg.r11, loc.addr(0, reg.r13))
                self.mc.STD(reg.f0, loc.addr(0, reg.r11))
            run_asm(self.a)
            assert isclose(mem[0], 0.0)

    def test_cast_single_float_to_float(self):
        with lltype.scoped_alloc(DOUBLE_ARRAY_PTR.TO, 16) as mem:
            with ActivationRecordCtx(self):
                with LiteralPoolCtx(self) as pool:
                    pool.single_float(6.66)
                    pool.addr(mem)
                self.mc.LEY(reg.f1, loc.addr(0, reg.r13))
                ## cast short to long!
                self.mc.LDEBR(reg.f0, reg.f1) 
                self.mc.LG(reg.r11, loc.addr(4, reg.r13))
                self.mc.STD(reg.f0, loc.addr(0, reg.r11))
            run_asm(self.a)
            assert isclose(mem[0], 6.66, abs_tol=0.05)

    def test_cast_int64_to_float(self):
        with lltype.scoped_alloc(DOUBLE_ARRAY_PTR.TO, 16) as mem:
            with ActivationRecordCtx(self):
                with LiteralPoolCtx(self) as pool:
                    pool.int64(12345)
                    pool.addr(mem)
                self.mc.LG(reg.r12, loc.addr(0, reg.r13))
                # cast int to float!
                self.mc.CDGBR(reg.f0, reg.r12) 
                self.mc.LG(reg.r11, loc.addr(8, reg.r13))
                self.mc.STD(reg.f0, loc.addr(0, reg.r11))
            run_asm(self.a)
            assert isclose(mem[0], 12345.0)

    def test_float_cmp(self):
        with ActivationRecordCtx(self):
            with LiteralPoolCtx(self) as pool:
                pool.float(1.0)
                pool.float(2.0)
            self.mc.LD(reg.f0, loc.addr(0, reg.r13))
            self.mc.LD(reg.f1, loc.addr(8, reg.r13))
            self.mc.CDBR(reg.f0, reg.f1)
            self.mc.LGHI(reg.r2, loc.imm(0))
            self.mc.BCR(con.EQ, reg.r14) # must not branch
            self.mc.LGHI(reg.r2, loc.imm(1))
        self.a.jmpto(reg.r14)
        assert run_asm(self.a) == 1

    def pushpop_jitframe(self, registers):
        self.a._push_core_regs_to_jitframe(self.mc, registers)
        self.a._pop_core_regs_from_jitframe(self.mc, registers)

    def test_pushpop_jitframe_multiple_optimization(self):
        stored = []
        loaded = []
        def STMG(start, end, addr):
            stored.append((start, end))
        def STG(reg, addr):
            stored.append((reg,))
        def LMG(start, end, addr):
            loaded.append((start, end)) 
        def LG(reg, addr):
            loaded.append((reg,))
        self.mc.STMG = STMG
        self.mc.STG = STG
        self.mc.LMG = LMG
        self.mc.LG = LG

        r = reg

        # two sequences 10-11, 13-14
        self.pushpop_jitframe([r.r10, r.r11, r.r13, r.r14])
        assert stored == [(r.r10, r.r11), (r.r13, r.r14)]
        assert stored == loaded
        stored = []
        loaded = []

        # one sequence and on single
        self.pushpop_jitframe([r.r0, r.r1, r.r3])
        assert stored == [(r.r0, r.r1), (r.r3,)]
        assert stored == loaded
        stored = []
        loaded = []

        # single items
        self.pushpop_jitframe(r.registers[::2])
        assert stored == [(x,) for x in r.registers[::2]]
        assert stored == loaded
        stored = []
        loaded = []

        # large sequence 0-5 and one hole between
        self.pushpop_jitframe([r.r0, r.r1, r.r2, r.r3,
            r.r4, r.r5, r.r12, r.r13])
        assert stored == [(r.r0, r.r5), (r.r12, r.r13)]
        assert stored == loaded
        stored = []
        loaded = []

        # ensure there is just on instruction for the 'best case'
        self.pushpop_jitframe(r.registers)
        assert stored == [(r.r0, r.r15)]
        assert stored == loaded
        stored = []
        loaded = []

        # just one single
        for x in [r.r14, r.r0, r.r1, r.r15]:
            self.pushpop_jitframe([x])
            assert stored == [(x,)]
            assert stored == loaded
            stored = []
            loaded = []

        # unordered
        self.pushpop_jitframe([r.r14, r.r8, r.r4, r.r0])
        assert stored == [(r.r14,), (r.r8,), (r.r4,), (r.r0,)]
        assert stored == loaded
        stored = []
        loaded = []




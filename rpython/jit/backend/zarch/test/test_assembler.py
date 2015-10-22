import struct
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
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.jit.metainterp.history import JitCellToken
from rpython.jit.backend.model import CompiledLoopToken
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rtyper.annlowlevel import llhelper
from rpython.rlib.objectmodel import specialize
from rpython.rlib.debug import ll_assert
from rpython.rlib.longlong2float import float2longlong

CPU = getcpuclass()

def byte_count(func):
    return func._byte_count

def BFL(value):
    #assert 0x0000000000000000 == float2longlong(0.0)
    #assert 0x8000000000000000 == abs(float2longlong(-0.0))
    #assert hex(0xc02e000000000000) == hex(abs(float2longlong(-15.0)))
    return struct.pack('>q', float2longlong(value))

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
            is AssemblerZARCH.emit_op_int_add.im_func

    def test_byte_count_instr(self):
        byte_count(self.mc.BRC) == 4
        byte_count(self.mc.LG) == 6

    def test_load_small_int_to_reg(self):
        self.a.mc.LGHI(reg.r2, loc.imm(123))
        self.a.jmpto(reg.r14)
        assert run_asm(self.a) == 123

    def test_prolog_epilog(self):
        self.a.gen_func_prolog()
        self.a.mc.LGHI(reg.r2, loc.imm(123))
        self.a.gen_func_epilog()
        assert run_asm(self.a) == 123

    def test_simple_func(self):
        # enter
        self.a.mc.STMG(reg.r11, reg.r15, loc.addr(-96, reg.sp))
        self.a.mc.AHI(reg.sp, loc.imm(-96))
        # from the start of BRASL to end of jmpto there are 8+6 bytes
        self.a.mc.BRASL(reg.r14, loc.imm(8+6))
        self.a.mc.LMG(reg.r11, reg.r15, loc.addr(0, reg.sp))
        self.a.jmpto(reg.r14)

        addr = self.a.mc.get_relative_pos()
        assert addr & 0x1 == 0
        self.a.gen_func_prolog()
        self.a.mc.LGHI(reg.r2, loc.imm(321))
        self.a.gen_func_epilog()
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
        self.a.gen_func_prolog()
        self.a.mc.BRAS(reg.r13, loc.imm(8 + byte_count(self.mc.BRAS)))
        self.a.mc.write('\x08\x07\x06\x05\x04\x03\x02\x01')
        self.a.mc.LG(reg.r2, loc.addr(0, reg.r13))
        self.a.gen_func_epilog()
        assert run_asm(self.a) == 0x0807060504030201

    def label(self, name, func=False):
        self.mc.mark_op(name)
        class ctxmgr(object):
            def __enter__(_self):
                if func:
                    self.a.gen_func_prolog()
            def __exit__(_self, a, b, c):
                if func:
                    self.a.gen_func_epilog()
                self.mc.mark_op(name + '.end')
        return ctxmgr()

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
        with self.label('func', func=True):
            with self.label('lit'):
                self.mc.BRAS(reg.r13, loc.imm(0))
            self.mc.write('\x00\x00\x00\x00\x00\x00\x00\x00')
            self.jump_here(self.mc.BRAS, 'lit')
            # recurse X times
            self.mc.XGR(reg.r2, reg.r2)
            self.mc.LGHI(reg.r9, loc.imm(15))
            with self.label('L1'):
                self.mc.BRAS(reg.r14, loc.imm(0))
            with self.label('rec', func=True):
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
        with self.label('func', func=True):
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
        with self.label('func', func=True):
            with self.label('lit'):
                self.mc.BRAS(reg.r13, loc.imm(0))
            self.mc.write(BFL(-15.0))
            self.jump_here(self.mc.BRAS, 'lit')
            self.mc.LD(reg.f0, loc.addr(0, reg.r13))
            self.mc.CGDBR(reg.r2, msk.RND_CURMODE, reg.f0)
        self.a.jmpto(reg.r14)
        assert run_asm(self.a) == -15

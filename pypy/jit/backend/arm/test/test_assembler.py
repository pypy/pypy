from pypy.jit.backend.arm.arch import arm_int_div, arm_int_div_sign
from pypy.jit.backend.arm import conditions as c
from pypy.jit.backend.arm import registers as r
from pypy.jit.backend.arm.arch import WORD
from pypy.jit.backend.arm.assembler import AssemblerARM
from pypy.jit.backend.arm.codebuilder import ARMv7InMemoryBuilder
from pypy.jit.backend.arm.test.support import skip_unless_arm, run_asm
from pypy.jit.metainterp.resoperation import rop

from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.lltypesystem import lltype, rffi, llmemory

skip_unless_arm()

class TestRunningAssembler():
    def setup_method(self, method):
        self.a = AssemblerARM(None)
        self.a.setup_mc()

    def test_make_operation_list(self):
        i = rop.INT_ADD
        assert self.a.operations[i] is AssemblerARM.emit_op_int_add.im_func

    def test_load_small_int_to_reg(self):
        self.a.gen_func_prolog()
        self.a.mc.gen_load_int(r.r0.value, 123)
        self.a.gen_func_epilog()
        assert run_asm(self.a) == 123

    def test_load_medium_int_to_reg(self):
        self.a.gen_func_prolog()
        self.a.mc.gen_load_int(r.r0.value, 0xBBD7)
        self.a.gen_func_epilog()
        assert run_asm(self.a) == 48087

    def test_load_int_to_reg(self):
        self.a.gen_func_prolog()
        self.a.mc.gen_load_int(r.r0.value, 0xFFFFFF85)
        self.a.gen_func_epilog()
        assert run_asm(self.a) == -123

    def test_load_neg_int_to_reg(self):
        self.a.gen_func_prolog()
        self.a.mc.gen_load_int(r.r0.value, -110)
        self.a.gen_func_epilog()
        assert run_asm(self.a) == -110

    def test_load_neg_int_to_reg2(self):
        self.a.gen_func_prolog()
        self.a.mc.gen_load_int(r.r0.value, -3)
        self.a.gen_func_epilog()
        assert run_asm(self.a) == -3


    def test_or(self):
        self.a.gen_func_prolog()
        self.a.mc.MOV_ri(r.r1.value, 8)
        self.a.mc.MOV_ri(r.r2.value, 8)
        self.a.mc.ORR_rr(r.r0.value, r.r1.value, r.r2.value, 4)
        self.a.gen_func_epilog()
        assert run_asm(self.a) == 0x88

    def test_sub(self):
        self.a.gen_func_prolog()
        self.a.mc.gen_load_int(r.r1.value, 123456)
        self.a.mc.SUB_ri(r.r0.value, r.r1.value, 123)
        self.a.gen_func_epilog()
        assert run_asm(self.a) == 123333

    def test_cmp(self):
        self.a.gen_func_prolog()
        self.a.mc.gen_load_int(r.r1.value, 22)
        self.a.mc.CMP_ri(r.r1.value, 123)
        self.a.mc.MOV_ri(r.r0.value, 1, c.LE)
        self.a.mc.MOV_ri(r.r0.value, 0, c.GT)
        self.a.gen_func_epilog()
        assert run_asm(self.a) == 1

    def test_int_le_false(self):
        self.a.gen_func_prolog()
        self.a.mc.gen_load_int(r.r1.value, 2222)
        self.a.mc.CMP_ri(r.r1.value, 123)
        self.a.mc.MOV_ri(r.r0.value, 1, c.LE)
        self.a.mc.MOV_ri(r.r0.value, 0, c.GT)
        self.a.gen_func_epilog()
        assert run_asm(self.a) == 0

    def test_simple_jump(self):
        self.a.gen_func_prolog()
        self.a.mc.MOV_ri(r.r1.value, 1)
        loop_head = self.a.mc.curraddr()
        self.a.mc.CMP_ri(r.r1.value, 0) # z=0, z=1
        self.a.mc.MOV_ri(r.r1.value, 0, cond=c.NE)
        self.a.mc.MOV_ri(r.r1.value, 7, cond=c.EQ)
        self.a.mc.B(loop_head, c.NE, some_reg = r.r4)
        self.a.mc.MOV_rr(r.r0.value, r.r1.value)
        self.a.gen_func_epilog()
        assert run_asm(self.a) == 7

    def test_jump(self):
        self.a.gen_func_prolog()
        self.a.mc.MOV_ri(r.r1.value, 1)
        loop_head = self.a.mc.curraddr()
        self.a.mc.ADD_ri(r.r1.value, r.r1.value, 1)
        self.a.mc.CMP_ri(r.r1.value, 9)
        self.a.mc.B(loop_head, c.NE, some_reg = r.r4)
        self.a.mc.MOV_rr(r.r0.value, r.r1.value)
        self.a.gen_func_epilog()
        assert run_asm(self.a) == 9

    def test_jump_with_inline_address(self):
        self.a.gen_func_prolog()
        self.a.mc.MOV_ri(r.r1.value, 1)
        loop_head = self.a.mc.curraddr()
        self.a.mc.ADD_ri(r.r1.value, r.r1.value, 1)
        self.a.mc.CMP_ri(r.r1.value, 9)
        self.a.mc.LDR_ri(r.pc.value, r.pc.value,
        imm=self.a.epilog_size, cond=c.NE) # we want to read after the last instr. of gen_func_prolog
        self.a.mc.MOV_rr(r.r0.value, r.r1.value)
        self.a.gen_func_epilog()
        self.a.mc.write32(loop_head)
        assert run_asm(self.a) == 9


    def test_call_python_func(self):
        functype = lltype.Ptr(lltype.FuncType([lltype.Signed], lltype.Signed))
        call_addr = rffi.cast(lltype.Signed, llhelper(functype, callme))
        self.a.gen_func_prolog()
        self.a.mc.MOV_ri(r.r0.value, 123)
        self.a.mc.BL(call_addr)
        self.a.gen_func_epilog()
        assert run_asm(self.a) == 133

    def test_division(self):
        self.a.gen_func_prolog()
        self.a.mc.MOV_ri(r.r0.value, 123)
        self.a.mc.MOV_ri(r.r1.value, 2)

        # call to div
        self.a.mc.PUSH(range(2, 12))
        div_addr = rffi.cast(lltype.Signed, llhelper(arm_int_div_sign, arm_int_div))
        self.a.mc.BL(div_addr, some_reg=r.r2)
        self.a.mc.POP(range(2, 12))
        self.a.gen_func_epilog()
        assert run_asm(self.a) == 61

    def test_DIV(self):
        self.a.gen_func_prolog()
        self.a.mc.MOV_ri(r.r0.value, 123)
        self.a.mc.MOV_ri(r.r1.value, 2)
        self.a.mc.DIV()
        self.a.gen_func_epilog()
        assert run_asm(self.a) == 61

    def test_DIV2(self):
        self.a.gen_func_prolog()
        self.a.mc.gen_load_int(r.r0.value, -110)
        self.a.mc.gen_load_int(r.r1.value, 3)
        self.a.mc.DIV()
        self.a.gen_func_epilog()
        assert run_asm(self.a) == -36

    def test_DIV3(self):
        self.a.gen_func_prolog()
        self.a.mc.gen_load_int(r.r8.value, 110)
        self.a.mc.gen_load_int(r.r9.value, -3)
        self.a.mc.MOV_rr(r.r0.value, r.r8.value)
        self.a.mc.MOV_rr(r.r1.value, r.r9.value)
        self.a.mc.DIV()
        self.a.gen_func_epilog()
        assert run_asm(self.a) == -36


    def test_bl_with_conditional_exec(self):
        functype = lltype.Ptr(lltype.FuncType([lltype.Signed], lltype.Signed))
        call_addr = rffi.cast(lltype.Signed, llhelper(functype, callme))
        self.a.gen_func_prolog()
        self.a.mc.MOV_ri(r.r0.value, 123)
        self.a.mc.CMP_ri(r.r0.value, 1)
        self.a.mc.BL(call_addr, c.NE, some_reg=r.r1)
        self.a.gen_func_epilog()
        assert run_asm(self.a) == 133

def callme(inp):
    i = inp + 10
    return i


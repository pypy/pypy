from pypy.jit.backend.arm import registers as r
from pypy.jit.backend.arm import conditions as c
from pypy.jit.backend.arm.assembler import AssemblerARM
from pypy.jit.backend.arm.test.support import skip_unless_arm, run_asm
from pypy.jit.metainterp.resoperation import rop

skip_unless_arm()

class TestRunningAssembler():
    def setup_method(self, method):
        self.a = AssemblerARM(None)

    def test_make_operation_list(self):
        i = rop.INT_ADD
        assert self.a.operations[i] is AssemblerARM.emit_op_int_add.im_func

    def test_load_small_int_to_reg(self):
        self.a.gen_func_prolog()
        self.a.gen_load_int(r.r0, 123)
        self.a.gen_func_epilog()
        assert run_asm(self.a) == 123

    def test_load_medium_int_to_reg(self):
        self.a.gen_func_prolog()
        self.a.gen_load_int(r.r0, 0xBBD7)
        self.a.gen_func_epilog()
        assert run_asm(self.a) == 48087

    def test_load_int_to_reg(self):
        self.a.gen_func_prolog()
        self.a.gen_load_int(r.r0, 0xFFFFFF85)
        self.a.gen_func_epilog()
        assert run_asm(self.a) == -123


    def test_or(self):
        self.a.gen_func_prolog()
        self.a.mc.MOV_ri(r.r1, 8)
        self.a.mc.MOV_ri(r.r2, 8)
        self.a.mc.ORR_rr(r.r0, r.r1, r.r2, 4)
        self.a.gen_func_epilog()
        assert run_asm(self.a) == 0x88

    def test_sub(self):
        self.a.gen_func_prolog()
        self.a.gen_load_int(r.r1, 123456)
        self.a.mc.SUB_ri(r.r0, r.r1, 123)
        self.a.gen_func_epilog()
        assert run_asm(self.a) == 123333

    def test_cmp(self):
        self.a.gen_func_prolog()
        self.a.gen_load_int(r.r1, 22)
        self.a.mc.CMP(r.r1, 123)
        self.a.mc.MOV_ri(r.r0, 1, c.LE)
        self.a.mc.MOV_ri(r.r0, 0, c.GT)
        self.a.gen_func_epilog()
        assert run_asm(self.a) == 1

    def test_int_le_false(self):
        self.a.gen_func_prolog()
        self.a.gen_load_int(r.r1, 2222)
        self.a.mc.CMP(r.r1, 123)
        self.a.mc.MOV_ri(r.r0, 1, c.LE)
        self.a.mc.MOV_ri(r.r0, 0, c.GT)
        self.a.gen_func_epilog()
        assert run_asm(self.a) == 0

    def test_simple_jump(self):
        self.a.gen_func_prolog()
        self.a.mc.MOV_ri(r.r1, 1)
        loop_head = self.a.mc.curraddr()
        self.a.mc.CMP(r.r1, 0) # z=0, z=1
        self.a.mc.MOV_ri(r.r1, 0, cond=c.NE)
        self.a.mc.MOV_ri(r.r1, 7, cond=c.EQ)
        self.a.gen_load_int(r.r4, loop_head, cond=c.NE)
        self.a.mc.MOV_rr(r.pc, r.r4, cond=c.NE)
        self.a.mc.MOV_rr(r.r0, r.r1)
        self.a.gen_func_epilog()
        assert run_asm(self.a) == 7

    def test_jump(self):
        self.a.gen_func_prolog()
        self.a.mc.MOV_ri(r.r1, 1)
        loop_head = self.a.mc.curraddr()
        self.a.mc.ADD_ri(r.r1, r.r1, 1)
        self.a.mc.CMP(r.r1, 9)
        self.a.gen_load_int(r.r4, loop_head, cond=c.NE)
        self.a.mc.MOV_rr(r.pc, r.r4, cond=c.NE)
        self.a.mc.MOV_rr(r.r0, r.r1)
        self.a.gen_func_epilog()
        assert run_asm(self.a) == 9



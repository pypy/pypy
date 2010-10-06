from pypy.jit.backend.arm import registers as r
from pypy.jit.backend.arm.assembler import AssemblerARM
from pypy.jit.backend.arm.test.support import skip_unless_arm, run_asm

skip_unless_arm()

class TestRunningAssembler():
    def setup_method(self, method):
        self.a = AssemblerARM(None)

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

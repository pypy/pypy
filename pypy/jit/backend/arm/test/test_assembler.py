from pypy.jit.backend.arm import registers as r
from pypy.jit.backend.arm.assembler import AssemblerARM
from pypy.jit.backend.arm.test.support import skip_unless_arm, run_asm

class TestRunningAssembler():
    def setup_method(self, method):
        self.a = AssemblerARM(None)

    @skip_unless_arm
    def test_load_small_int_to_reg(self):
        self.a.gen_preamble()
        self.a.gen_load_int(r.r0, 123)
        self.a.gen_out()
        assert run_asm(self.a) == 123

    @skip_unless_arm
    def test_load_medium_int_to_reg(self):
        self.a.gen_preamble()
        self.a.gen_load_int(r.r0, 0xBBD7)
        self.a.gen_out()
        assert run_asm(self.a) == 48087

    @skip_unless_arm
    def test_load_int_to_reg(self):
        self.a.gen_preamble()
        self.a.gen_load_int(r.r0, 0xFFFFFF85)
        self.a.gen_out()
        assert run_asm(self.a) == -123


    @skip_unless_arm
    def test_or(self):
        self.a.gen_preamble()
        self.a.mc.MOV_ri(r.r1, 8)
        self.a.mc.MOV_ri(r.r2, 8)
        self.a.mc.ORR_rr(r.r0, r.r1, r.r2, 4)
        self.a.gen_out()
        assert run_asm(self.a) == 0x88

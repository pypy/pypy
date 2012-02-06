from pypy.jit.backend.ppc import regalloc, register

class TestPPCRegisterManager(object):
    def test_allocate_scratch_register(self):
        rm = regalloc.PPCRegisterManager({})
        reg, box = rm.allocate_scratch_reg()
        assert reg in register.MANAGED_REGS
        assert rm.stays_alive(box) == False

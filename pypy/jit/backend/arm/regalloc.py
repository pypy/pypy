from pypy.jit.backend.llsupport.regalloc import FrameManager, \
        RegisterManager, compute_vars_longevity
from pypy.jit.backend.arm import registers as r
from pypy.jit.backend.arm import locations

class ARMRegisterManager(RegisterManager):
    all_regs              = r.all_regs
    box_types             = None       # or a list of acceptable types
    no_lower_byte_regs    = all_regs
    save_around_call_regs = all_regs

    def __init__(self, longevity, frame_manager=None, assembler=None):
        RegisterManager.__init__(self, longevity, frame_manager, assembler)

    def update_bindings(self, enc, inputargs):
        j = 0
        for i in range(len(inputargs)):
            while enc[j] == '\xFE':
                j += 1
            self.force_allocate_reg(inputargs[i], selected_reg=r.all_regs[ord(enc[j])])
            j += 1

    def convert_to_imm(self, c):
        return locations.ImmLocation(c.value)

class ARMFrameManager(FrameManager):
    @staticmethod
    def frame_pos(loc, type):
        pass

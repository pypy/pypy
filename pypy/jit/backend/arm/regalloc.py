from pypy.jit.backend.llsupport.regalloc import FrameManager, \
        RegisterManager, compute_vars_longevity
from pypy.jit.backend.arm import registers as r

class ARMRegisterManager(RegisterManager):
    all_regs              = r.all_regs
    box_types             = None       # or a list of acceptable types
    no_lower_byte_regs    = r.all_regs
    save_around_call_regs = all_regs

    def __init__(self, longevity, frame_manager=None, assembler=None):
        RegisterManager.__init__(self, longevity, frame_manager, assembler)

    def update_bindings(self, enc, inputargs):
        j = 0
        for i in range(len(inputargs)):
            while enc[j] == '\xFE':
                j += 1
            self.try_allocate_reg(inputargs[i], ord(enc[j]))
            j += 1

class ARMFrameManager(FrameManager):
    @staticmethod
    def frame_pos(loc, type):
        pass

#class RegAlloc(object):
#    def __init__(self, assembler, translate_support_code=False):
#        self.assembler = assembler
#        self.translate_support_code = translate_support_code
#        self.fm = None
#
#    def _prepare(self, inputargs, operations):
#        longevity = compute_vars_longevity(inputargs, operations)
#        self.rm = ARMRegisterManager(longevity, self.fm)
#
#    def prepare_loop(self, inputargs, operations, looptoken):
#        self._prepare(inputargs, operations)
#
#    def force_allocate_reg(self, v, forbidden_vars=[], selected_reg=None,
#                           need_lower_byte=False):
#        return self.rm.force_allocate_reg(v, forbidden_vars, selected_reg, need_lower_byte)

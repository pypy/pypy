from rpython.jit.backend.ppc.arch import IS_PPC_64, WORD
import rpython.jit.backend.ppc.register as r
from rpython.jit.metainterp.history import INT
from rpython.jit.backend.llsupport.callbuilder import AbstractCallBuilder
from rpython.jit.backend.ppc.jump import remap_frame_layout


def follow_jump(addr):
    # xxx implement me
    return addr


class CallBuilder(AbstractCallBuilder):

    def __init__(self, assembler, fnloc, arglocs, resloc):
        AbstractCallBuilder.__init__(self, assembler, fnloc, arglocs,
                                     resloc, restype=INT, ressize=None)

    def prepare_arguments(self):
        assert IS_PPC_64

        # First, copy fnloc into r2
        self.asm.regalloc_mov(self.fnloc, r.r2)

        # Prepare arguments
        arglocs = self.arglocs
        argtypes = self.argtypes

        assert len(argtypes) <= 8, "XXX"
        non_float_locs = arglocs
        non_float_regs = (           # XXX
            [r.r3, r.r4, r.r5, r.r6, r.r7, r.r8, r.r9, r.r10][:len(argtypes)])

        remap_frame_layout(self.asm, non_float_locs, non_float_regs,
                           r.SCRATCH)


    def push_gcmap(self):
        pass  # XXX

    def pop_gcmap(self):
        pass  # XXX

    def emit_raw_call(self):
        # Load the function descriptor (currently in r2) from memory:
        #  [r2 + 0]  -> ctr
        #  [r2 + 16] -> r11
        #  [r2 + 8]  -> r2  (= TOC)
        self.mc.ld(r.SCRATCH.value, r.r2.value, 0)
        self.mc.ld(r.r11.value, r.r2.value, 16)
        self.mc.mtctr(r.SCRATCH.value)
        self.mc.ld(r.TOC.value, r.r2.value, 8)
        # Call it
        self.mc.bctrl()

    def restore_stack_pointer(self):
        pass  # XXX

    def load_result(self):
        pass

from rpython.jit.backend.ppc.arch import IS_PPC_64, WORD, PARAM_SAVE_AREA_OFFSET
from rpython.jit.backend.ppc.arch import IS_BIG_ENDIAN, IS_LITTLE_ENDIAN
import rpython.jit.backend.ppc.register as r
from rpython.jit.metainterp.history import INT, FLOAT
from rpython.jit.backend.llsupport.callbuilder import AbstractCallBuilder
from rpython.jit.backend.ppc.jump import remap_frame_layout


def follow_jump(addr):
    # xxx implement me
    return addr


class CallBuilder(AbstractCallBuilder):
    GPR_ARGS = [r.r3, r.r4, r.r5, r.r6, r.r7, r.r8, r.r9, r.r10]
    FPR_ARGS = r.MANAGED_FP_REGS
    assert FPR_ARGS == [r.f1, r.f2, r.f3, r.f4, r.f5, r.f6, r.f7,
                        r.f8, r.f9, r.f10, r.f11, r.f12, r.f13]

    if IS_BIG_ENDIAN:
        FNREG = r.r2
    else:
        FNREG = r.r12

    def __init__(self, assembler, fnloc, arglocs, resloc):
        AbstractCallBuilder.__init__(self, assembler, fnloc, arglocs,
                                     resloc, restype=INT, ressize=None)

    def prepare_arguments(self):
        assert IS_PPC_64
        self.subtracted_to_sp = 0

        # Prepare arguments
        arglocs = self.arglocs
        num_args = len(arglocs)

        non_float_locs = []
        non_float_regs = []
        float_locs = []
        for i in range(min(num_args, 8)):
            if arglocs[i].type != FLOAT:
                non_float_locs.append(arglocs[i])
                non_float_regs.append(self.GPR_ARGS[i])
            else:
                float_locs.append(arglocs[i])
        # now 'non_float_locs' and 'float_locs' together contain the
        # locations of the first 8 arguments

        if num_args > 8:
            # We need to make a larger PPC stack frame, as shown on the
            # picture in arch.py.  It needs to be 48 bytes + 8 * num_args.
            # The new SP back chain location should point to the top of
            # the whole stack frame, i.e. jumping over both the existing
            # fixed-sise part and the new variable-sized part.
            base = PARAM_SAVE_AREA_OFFSET
            varsize = base + 8 * num_args
            varsize = (varsize + 15) & ~15    # align
            self.mc.load(r.SCRATCH2.value, r.SP.value, 0)    # SP back chain
            self.mc.store_update(r.SCRATCH2.value, r.SP.value, -varsize)
            self.subtracted_to_sp = varsize

            # In this variable-sized part, only the arguments from the 8th
            # one need to be written, starting at SP + 112
            for n in range(8, num_args):
                loc = arglocs[n]
                if loc.type != FLOAT:
                    # after the 8th argument, a non-float location is
                    # always stored in the stack
                    if loc.is_reg():
                        src = loc.value
                    else:
                        src = r.r2
                        self.asm.regalloc_mov(loc, src)
                    self.mc.std(src.value, r.SP.value, base + 8 * n)
                else:
                    # the first 13 floating-point arguments are all passed
                    # in the registers f1 to f13, independently on their
                    # index in the complete list of arguments
                    if len(float_locs) < len(self.FPR_ARGS):
                        float_locs.append(loc)
                    else:
                        if loc.is_fp_reg():
                            src = loc.value
                        else:
                            src = r.FP_SCRATCH
                            self.asm.regalloc_mov(loc, src)
                        self.mc.stfd(src.value, r.SP.value, base + 8 * n)

        # We must also copy fnloc into FNREG
        non_float_locs.append(self.fnloc)
        non_float_regs.append(self.FNREG)

        if float_locs:
            assert len(float_locs) <= len(self.FPR_ARGS)
            remap_frame_layout(self.asm, float_locs,
                               self.FPR_ARGS[:len(float_locs)],
                               r.FP_SCRATCH)

        remap_frame_layout(self.asm, non_float_locs, non_float_regs,
                           r.SCRATCH)


    def push_gcmap(self):
        pass  # XXX

    def pop_gcmap(self):
        pass  # XXX

    def emit_raw_call(self):
        if IS_BIG_ENDIAN:
            # Load the function descriptor (currently in r2) from memory:
            #  [r2 + 0]  -> ctr
            #  [r2 + 16] -> r11
            #  [r2 + 8]  -> r2  (= TOC)
            assert self.FNREG is r.r2
            self.mc.ld(r.SCRATCH.value, r.r2.value, 0)
            self.mc.ld(r.r11.value, r.r2.value, 16)
            self.mc.mtctr(r.SCRATCH.value)
            self.mc.ld(r.TOC.value, r.r2.value, 8)   # must be last: TOC is r2
        elif IS_LITTLE_ENDIAN:
            assert self.FNREG is r.r12
            self.mc.mtctr(r.r12.value)
        # Call the function
        self.mc.bctrl()

    def restore_stack_pointer(self):
        if self.subtracted_to_sp != 0:
            self.mc.addi(r.SP.value, r.SP.value, self.subtracted_to_sp)

    def load_result(self):
        pass

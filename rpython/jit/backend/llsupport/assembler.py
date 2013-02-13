
from rpython.rlib.rarithmetic import r_uint
from rpython.jit.backend.llsupport.symbolic import WORD
from rpython.jit.metainterp.history import REF

class GuardToken(object):
    def __init__(self, cpu, gcmap, faildescr, failargs, fail_locs, exc,
                 frame_depth, is_guard_not_invalidated, is_guard_not_forced):
        self.cpu = cpu
        self.faildescr = faildescr
        self.failargs = failargs
        self.fail_locs = fail_locs
        self.gcmap = self.compute_gcmap(gcmap, failargs,
                                        fail_locs, frame_depth)
        self.exc = exc
        self.is_guard_not_invalidated = is_guard_not_invalidated
        self.is_guard_not_forced = is_guard_not_forced

    def compute_gcmap(self, gcmap, failargs, fail_locs, frame_depth):
        # note that regalloc has a very similar compute, but
        # one that does iteration over all bindings, so slightly different,
        # eh
        input_i = 0
        for i in range(len(failargs)):
            arg = failargs[i]
            if arg is None:
                continue
            loc = fail_locs[input_i]
            input_i += 1
            if arg.type == REF:
                loc = fail_locs[i]
                if loc.is_reg():
                    val = self.cpu.all_reg_indexes[loc.value]
                else:
                    val = loc.get_position() + self.cpu.JITFRAME_FIXED_SIZE
                gcmap[val // WORD // 8] |= r_uint(1) << (val % (WORD * 8))
        return gcmap


class BaseAssembler(object):
    """ Base class for Assembler generator in real backends
    """
    def rebuild_faillocs_from_descr(self, descr, inputargs):
        locs = []
        GPR_REGS = len(self.cpu.gen_regs)
        XMM_REGS = len(self.cpu.float_regs)
        input_i = 0
        if self.cpu.IS_64_BIT:
            coeff = 1
        else:
            coeff = 2
        for pos in descr.rd_locs:
            if pos == -1:
                continue
            elif pos < GPR_REGS * WORD:
                locs.append(self.cpu.gen_regs[pos // WORD])
            elif pos < (GPR_REGS + XMM_REGS * coeff) * WORD:
                pos = (pos // WORD - GPR_REGS) // coeff
                locs.append(self.cpu.float_regs[pos])
            else:
                i = pos // WORD - self.cpu.JITFRAME_FIXED_SIZE
                assert i >= 0
                tp = inputargs[input_i].type
                locs.append(self.new_stack_loc(i, pos, tp))
            input_i += 1
        return locs

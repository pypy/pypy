from pypy.jit.backend.ppc.ppcgen.helper.assembler import gen_emit_cmp_op
import pypy.jit.backend.ppc.ppcgen.condition as c
import pypy.jit.backend.ppc.ppcgen.register as r
from pypy.jit.backend.ppc.ppcgen.arch import GPR_SAVE_AREA, IS_PPC_32, WORD

from pypy.jit.metainterp.history import LoopToken, AbstractFailDescr

class GuardToken(object):
    def __init__(self, descr, failargs, faillocs, offset, fcond=c.NE,
                                        save_exc=False, is_invalidate=False):
        self.descr = descr
        self.offset = offset
        self.is_invalidate = is_invalidate
        self.failargs = failargs
        self.faillocs = faillocs
        self.save_exc = save_exc
        self.fcond=fcond

class OpAssembler(object):
        
    # ********************************************************
    # *               I N T    O P E R A T I O N S           *
    # ********************************************************

    def emit_int_add(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        if l0.is_imm():
            self.mc.addi(res.value, l1.value, l0.value)
        elif l1.is_imm():
            self.mc.addi(res.value, l0.value, l1.value)
        else:
            self.mc.add(res.value, l0.value, l1.value)

    def emit_int_sub(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        if l0.is_imm():
            self.mc.load_imm(r.r0, l0.value)
            self.mc.sub(res.value, r.r0.value, l1.value)
        elif l1.is_imm():
            self.mc.subi(res.value, l0.value, l1.value)
        else:
            self.mc.sub(res.value, l0.value, l1.value)
 
    def emit_int_mul(self, op, arglocs, regalloc):
        reg1, reg2, res = arglocs
        self.mc.mullw(res.value, reg1.value, reg2.value)

    def emit_int_floordiv(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        if IS_PPC_32:
            div = self.mc.divw
        else:
            div = self.mc.divd

        if l0.is_imm():
            self.mc.load_imm(r.r0, l0.value)
            div(res.value, r.r0.value, l1.value)
        elif l1.is_imm():
            self.mc.load_imm(r.r0, l1.value)
            div(res.value, l0.value, r.r0.value)
        else:
            self.mc.divw(res.value, l0.value, l1.value)

    emit_int_le = gen_emit_cmp_op(c.LE)   

    def _emit_guard(self, op, arglocs, fcond, save_exc=False,
            is_guard_not_invalidated=False):
        descr = op.getdescr()
        assert isinstance(descr, AbstractFailDescr)
        pos = self.mc.currpos()
        self.mc.nop()     # has to be patched later on
        self.pending_guards.append(GuardToken(descr,
                                   failargs=op.getfailargs(),
                                   faillocs=arglocs,
                                   offset=pos,
                                   fcond=fcond,
                                   is_invalidate=is_guard_not_invalidated,
                                   save_exc=save_exc))

    def emit_guard_true(self, op, arglocs, regalloc):
        l0 = arglocs[0]
        failargs = arglocs[1:]
        self.mc.cmpi(l0.value, 0)
        self._emit_guard(op, failargs, c.EQ)
        #                        #      ^^^^ If this condition is met,
        #                        #           then the guard fails.

    def emit_finish(self, op, arglocs, regalloc):
        self.gen_exit_stub(op.getdescr(), op.getarglist(), arglocs)

    def emit_jump(self, op, arglocs, regalloc):
        descr = op.getdescr()
        assert isinstance(descr, LoopToken)
        if descr._ppc_bootstrap_code == 0:
            curpos = self.mc.get_rel_pos()
            self.mc.b(descr._ppc_loop_code - curpos)
        else:
            assert 0, "case not implemented yet"

    def nop(self):
        self.mc.ori(0, 0, 0)

    def branch_abs(self, address):
        self.load_imm(r.r0.value, address)
        self.mc.mtctr(0)
        self.mc.bctr()

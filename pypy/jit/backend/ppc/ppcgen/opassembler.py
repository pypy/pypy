from pypy.jit.backend.ppc.ppcgen.helper.assembler import gen_emit_cmp_op
import pypy.jit.backend.ppc.ppcgen.condition as c
import pypy.jit.backend.ppc.ppcgen.register as r
from pypy.jit.backend.ppc.ppcgen.arch import GPR_SAVE_AREA, IS_PPC_32, WORD

from pypy.jit.metainterp.history import LoopToken

class OpAssembler(object):
        
    def emit_int_add(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        if l0.is_imm():
            self.mc.addi(res.value, l1.value, l0.value)
        elif l1.is_imm():
            self.mc.addi(res.value, l0.value, l1.value)
        else:
            self.add(res.value, l0.value, l1.value)
   
    emit_int_le = gen_emit_cmp_op(c.LE)   

    def _guard_epilogue(self, op, failargs):
        fail_descr = op.getdescr()
        fail_index = self._get_identifier_from_descr(fail_descr)
        fail_descr.index = fail_index
        self.cpu.saved_descr[fail_index] = fail_descr
        numops = self.mc.get_number_of_ops()
        self.mc.beq(0)
        reglist = []
        for failarg in failargs:
            if failarg is None:
                reglist.append(None)
            else:
                reglist.append(failarg)
        self.patch_list.append((numops, fail_index, op, reglist))

    def _emit_guard(self, op, arglocs, save_exc=False,
            is_guard_not_invalidated=False):
        descr = op.getdescr()
        assert isinstance(descr, AbstractFailDescr)
        pos = self.get_relative_pos()
        self.mc.b(0)   # has to be patched later on
        self.pending_guards.append(GuardToken(descr,
                                   failargs=op.getfailargs(),
                                   faillocs=arglocs,
                                   offset=pos,
                                   is_invalidate=is_guard_not_invalidated,
                                   save_exc=save_exc))

    def emit_guard_true(self, op, arglocs, regalloc):
        l0 = arglocs[0]
        failargs = arglocs[1:]
        self.mc.cmpi(l0.value, 0)
        self._guard_epilogue(op, failargs)

    def emit_finish(self, op, arglocs, regalloc):
        descr = op.getdescr()
        identifier = self._get_identifier_from_descr(descr)
        self.cpu.saved_descr[identifier] = descr
        args = op.getarglist()
        for index, arg in enumerate(arglocs):
            addr = self.fail_boxes_int.get_addr_for_num(index)
            self.store_reg(arg, addr)
        self.load_imm(r.RES, identifier) # set return value
        self.branch_abs(self.exit_code_adr)

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
        self.load_imm(r.r0, address)
        self.mc.mtctr(0)
        self.mc.bctr()

#!/usr/bin/env python

from rpython.jit.backend.llsupport.assembler import BaseAssembler
from rpython.jit.backend.riscv import registers as r
from rpython.jit.metainterp.resoperation import rop


class OpAssembler(BaseAssembler):
    def emit_op_int_add(self, op, arglocs):
        l0, l1, res = arglocs
        assert not l0.is_imm()
        if l1.is_imm():
            self.mc.ADDI(res.value, l0.value, l1.value)
        else:
            self.mc.ADD(res.value, l0.value, l1.value)

    def emit_op_float_add(self, op, arglocs):
        l0, l1, res = arglocs
        self.mc.FADD_D(res.value, l0.value, l1.value)

    def emit_op_finish(self, op, arglocs):
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        if len(arglocs) > 0:
            [return_val] = arglocs
            if return_val.is_fp_reg():
                self.mc.store_float(return_val.value, r.jfp.value, base_ofs)
            else:
                self.mc.store_int(return_val.value, r.jfp.value, base_ofs)

        faildescrindex = self.get_gcref_from_faildescr(op.getdescr())
        self.store_jf_descr(faildescrindex)

        self._call_footer(self.mc)


def not_implemented_op(self, op, arglocs):
    print "[riscv/asm] %s not implemented" % op.getopname()
    raise NotImplementedError(op)

def not_implemented_comp_op(self, op, arglocs):
    print "[riscv/asm] %s not implemented" % op.getopname()
    raise NotImplementedError(op)

def not_implemented_guard_op(self, op, guard_op, arglocs, guard_branch_inst):
    print "[riscv/asm] %s not implemented" % op.getopname()
    raise NotImplementedError(op)

asm_operations = [not_implemented_op] * (rop._LAST + 1)
asm_guard_operations = [not_implemented_guard_op] * (rop._LAST + 1)
asm_comp_operations = [not_implemented_comp_op] * (rop._LAST + 1)

for name, value in OpAssembler.__dict__.iteritems():
    if name.startswith('emit_op_'):
        opname = name[len('emit_op_'):]
        num = getattr(rop, opname.upper())
        asm_operations[num] = value
    elif name.startswith('emit_guard_op_'):
        opname = name[len('emit_guard_op_'):]
        num = getattr(rop, opname.upper())
        asm_guard_operations[num] = value
    elif name.startswith('emit_comp_op_'):
        opname = name[len('emit_comp_op_'):]
        num = getattr(rop, opname.upper())
        asm_comp_operations[num] = value

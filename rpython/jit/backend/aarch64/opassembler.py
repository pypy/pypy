
from rpython.jit.backend.aarch64 import registers as r
from rpython.jit.backend.llsupport.assembler import GuardToken, BaseAssembler

class ResOpAssembler(BaseAssembler):
    def emit_op_int_add(self, op, arglocs):
        return self.int_add_impl(op, arglocs)

    emit_op_nursery_ptr_increment = emit_op_int_add

    def int_add_impl(self, op, arglocs, ovfcheck=False):
        l0, l1, res = arglocs
        if ovfcheck:
            XXX
            s = 1
        else:
            s = 0
        if l0.is_imm():
            self.mc.ADD_ri(res.value, l1.value, imm=l0.value, s=s)
        elif l1.is_imm():
            self.mc.ADD_ri(res.value, l0.value, imm=l1.value, s=s)
        else:
            self.mc.ADD_rr(res.value, l0.value, l1.value)

    def emit_op_increment_debug_counter(self, op, arglocs):
        return # XXXX
        base_loc, value_loc = arglocs
        self.mc.LDR_ri(value_loc.value, base_loc.value, 0)
        self.mc.ADD_ri(value_loc.value, value_loc.value, 1)
        self.mc.STR_ri(value_loc.value, base_loc.value, 0)

    def emit_op_finish(self, op, arglocs):
        self.mc.MOV_rr(r.x0.value, r.fp.value)
        # exit function
        self.gen_func_epilog()

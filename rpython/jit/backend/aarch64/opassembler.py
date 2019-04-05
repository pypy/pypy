
from rpython.jit.metainterp.history import (AbstractFailDescr, ConstInt,
                                            INT, FLOAT, REF)
from rpython.jit.backend.aarch64 import registers as r
from rpython.jit.backend.arm import conditions as c
from rpython.jit.backend.aarch64.arch import JITFRAME_FIXED_SIZE
from rpython.jit.backend.llsupport.assembler import GuardToken, BaseAssembler
from rpython.jit.backend.llsupport.gcmap import allocate_gcmap
from rpython.jit.metainterp.history import TargetToken


class ResOpAssembler(BaseAssembler):
    def emit_op_int_add(self, op, arglocs):
        return self.int_add_impl(op, arglocs)

    def int_sub_impl(self, op, arglocs, flags=0):
        l0, l1, res = arglocs
        if flags:
            xxx
            s = 1
        else:
            s = 0
        if l0.is_imm():
            value = l0.getint()
            assert value >= 0
            # reverse substract ftw
            XX
            self.mc.RSB_ri(res.value, l1.value, value)
        elif l1.is_imm():
            value = l1.getint()
            assert value >= 0
            self.mc.SUB_ri(res.value, l0.value, value)
        else:
            self.mc.SUB_rr(res.value, l0.value, l1.value)

    def emit_op_int_sub(self, op, arglocs):
        self.int_sub_impl(op, arglocs)

    emit_op_nursery_ptr_increment = emit_op_int_add

    def int_add_impl(self, op, arglocs, ovfcheck=False):
        l0, l1, res = arglocs
        if ovfcheck:
            XXX
            s = 1
        else:
            s = 0
        if l0.is_imm():
            self.mc.ADD_ri(res.value, l1.value, l0.value)
        elif l1.is_imm():
            self.mc.ADD_ri(res.value, l0.value, l1.value)
        else:
            self.mc.ADD_rr(res.value, l0.value, l1.value)

    def emit_int_comp_op(self, op, arglocs):
        l0, l1 = arglocs

        if l1.is_imm():
            xxx
            self.mc.CMP_ri(l0.value, imm=l1.getint(), cond=fcond)
        else:
            self.mc.CMP_rr(l0.value, l1.value)

    def emit_comp_op_int_lt(self, op, arglocs):
        self.emit_int_comp_op(op, arglocs)
        return c.LT

    def emit_comp_op_int_le(self, op, arglocs):
        self.emit_int_comp_op(op, arglocs)
        return c.LE

    def emit_op_increment_debug_counter(self, op, arglocs):
        return # XXXX
        base_loc, value_loc = arglocs
        self.mc.LDR_ri(value_loc.value, base_loc.value, 0)
        self.mc.ADD_ri(value_loc.value, value_loc.value, 1)
        self.mc.STR_ri(value_loc.value, base_loc.value, 0)

    def build_guard_token(self, op, frame_depth, arglocs, offset, fcond):
        descr = op.getdescr()
        assert isinstance(descr, AbstractFailDescr)

        gcmap = allocate_gcmap(self, frame_depth, JITFRAME_FIXED_SIZE)
        faildescrindex = self.get_gcref_from_faildescr(descr)
        token = GuardToken(self.cpu, gcmap, descr,
                                    failargs=op.getfailargs(),
                                    fail_locs=arglocs,
                                    guard_opnum=op.getopnum(),
                                    frame_depth=frame_depth,
                                    faildescrindex=faildescrindex)
        token.fcond = fcond
        return token

    def _emit_guard(self, op, fcond, arglocs, is_guard_not_invalidated=False):
        pos = self.mc.currpos()
        token = self.build_guard_token(op, arglocs[0].value, arglocs[1:], pos,
                                       fcond)
        token.offset = pos
        self.pending_guards.append(token)
        assert token.guard_not_invalidated() == is_guard_not_invalidated
        # For all guards that are not GUARD_NOT_INVALIDATED we emit a
        # breakpoint to ensure the location is patched correctly. In the case
        # of GUARD_NOT_INVALIDATED we use just a NOP, because it is only
        # eventually patched at a later point.
        if is_guard_not_invalidated:
            self.mc.NOP()
        else:
            self.mc.BRK()

    def emit_guard_op_guard_true(self, guard_op, fcond, arglocs):
        self._emit_guard(guard_op, fcond, arglocs)

    def emit_guard_op_guard_false(self, guard_op, fcond, arglocs):
        self._emit_guard(guard_op, c.get_opposite_of(fcond), arglocs)

    def load_condition_into_cc(self, loc):
        if not loc.is_core_reg():
            assert loc.is_stack()
            self.regalloc_mov(loc, r.ip0)
            loc = r.ip0
        self.mc.CMP_ri(loc.value, 0)

    def emit_op_guard_false(self, op, arglocs):
        self.load_condition_into_cc(arglocs[1])
        self._emit_guard(op, c.EQ, arglocs)

    def emit_op_label(self, op, arglocs):
        pass

    def emit_op_jump(self, op, arglocs):
        target_token = op.getdescr()
        assert isinstance(target_token, TargetToken)
        target = target_token._ll_loop_code
        if target_token in self.target_tokens_currently_compiling:
            self.mc.B_ofs(target)
        else:
            self.mc.BL(target)

    def emit_op_finish(self, op, arglocs):
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        if len(arglocs) > 0:
            [return_val] = arglocs
            self.store_reg(self.mc, return_val, r.fp, base_ofs)
        ofs = self.cpu.get_ofs_of_frame_field('jf_descr')

        faildescrindex = self.get_gcref_from_faildescr(op.getdescr())
        self.load_from_gc_table(r.ip0.value, faildescrindex)
        # XXX self.mov(fail_descr_loc, RawStackLoc(ofs))
        self.store_reg(self.mc, r.ip0, r.fp, ofs)
        if op.numargs() > 0 and op.getarg(0).type == REF:
            if self._finish_gcmap:
                # we're returning with a guard_not_forced_2, and
                # additionally we need to say that r0 contains
                # a reference too:
                self._finish_gcmap[0] |= r_uint(1)
                gcmap = self._finish_gcmap
            else:
                gcmap = self.gcmap_for_finish
            self.push_gcmap(self.mc, gcmap, store=True)
        elif self._finish_gcmap:
            # we're returning with a guard_not_forced_2
            gcmap = self._finish_gcmap
            self.push_gcmap(self.mc, gcmap, store=True)
        else:
            # note that the 0 here is redundant, but I would rather
            # keep that one and kill all the others
            ofs = self.cpu.get_ofs_of_frame_field('jf_gcmap')
            self.store_reg(self.mc, r.xzr, r.fp, ofs)
        self.mc.MOV_rr(r.x0.value, r.fp.value)
        # exit function
        self.gen_func_epilog()

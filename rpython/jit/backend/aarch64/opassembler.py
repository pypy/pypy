
from rpython.jit.metainterp.history import (AbstractFailDescr, ConstInt,
                                            INT, FLOAT, REF)
from rpython.jit.backend.aarch64 import registers as r
from rpython.jit.backend.arm import conditions as c
from rpython.jit.backend.aarch64.arch import JITFRAME_FIXED_SIZE
from rpython.jit.backend.llsupport.assembler import GuardToken, BaseAssembler
from rpython.jit.backend.llsupport.gcmap import allocate_gcmap
from rpython.jit.metainterp.history import TargetToken

def gen_comp_op(name, flag):
    def emit_op(self, op, arglocs):
        l0, l1, res = arglocs

        self.emit_int_comp_op(op, l0, l1)
        self.mc.CSET_r_flag(res.value, c.get_opposite_of(flag))
    emit_op.__name__ = name
    return emit_op

class ResOpAssembler(BaseAssembler):
    def int_sub_impl(self, op, arglocs, flags=0):
        l0, l1, res = arglocs
        if flags:
            s = 1
        else:
            s = 0
        if l1.is_imm():
            value = l1.getint()
            assert value >= 0
            self.mc.SUB_ri(res.value, l0.value, value, s)
        else:
            self.mc.SUB_rr(res.value, l0.value, l1.value, s)

    def emit_op_int_sub(self, op, arglocs):
        self.int_sub_impl(op, arglocs)

    def int_add_impl(self, op, arglocs, ovfcheck=False):
        l0, l1, res = arglocs
        assert not l0.is_imm()
        if ovfcheck:
            s = 1
        else:
            s = 0
        if l1.is_imm():
            self.mc.ADD_ri(res.value, l0.value, l1.value, s)
        else:
            self.mc.ADD_rr(res.value, l0.value, l1.value, s)

    def emit_op_int_add(self, op, arglocs):
        self.int_add_impl(op, arglocs)
    emit_op_nursery_ptr_increment = emit_op_int_add

    def emit_comp_op_int_add_ovf(self, op, arglocs):
        self.int_add_impl(op, arglocs, True)

    def emit_comp_op_int_sub_ovf(self, op, arglocs):
        self.int_sub_impl(op, arglocs, True)

    def emit_op_int_mul(self, op, arglocs):
        reg1, reg2, res = arglocs
        self.mc.MUL_rr(res.value, reg1.value, reg2.value)

    def emit_comp_op_int_mul_ovf(self, op, arglocs):
        reg1, reg2, res = arglocs
        self.mc.MUL_rr(res.value, reg1.value, reg2.value)
        xxx # what to do here?
        self.mc.SMULH_rr(res.value, reg1.value, reg2.value)
        self.mc.CMP_ri(r.ip0.value, 0)

    def emit_op_int_and(self, op, arglocs):
        l0, l1, res = arglocs
        self.mc.AND_rr(res.value, l0.value, l1.value)

    def emit_op_int_or(self, op, arglocs):
        l0, l1, res = arglocs
        self.mc.ORR_rr(res.value, l0.value, l1.value)

    def emit_op_int_xor(self, op, arglocs):
        l0, l1, res = arglocs
        self.mc.EOR_rr(res.value, l0.value, l1.value)

    def emit_op_int_lshift(self, op, arglocs):
        l0, l1, res = arglocs
        self.mc.LSL_rr(res.value, l0.value, l1.value)

    def emit_op_int_rshift(self, op, arglocs):
        l0, l1, res = arglocs
        self.mc.ASR_rr(res.value, l0.value, l1.value)

    def emit_op_uint_rshift(self, op, arglocs):
        l0, l1, res = arglocs
        self.mc.LSR_rr(res.value, l0.value, l1.value)

    def emit_op_uint_mul_high(self, op, arglocs):
        l0, l1, res = arglocs
        self.mc.UMULH_rr(res.value, l0.value, l1.value)

    def emit_int_comp_op(self, op, l0, l1):
        if l1.is_imm():
            self.mc.CMP_ri(l0.value, l1.getint())
        else:
            self.mc.CMP_rr(l0.value, l1.value)

    def emit_comp_op_int_lt(self, op, arglocs):
        self.emit_int_comp_op(op, arglocs[0], arglocs[1])
        return c.LT

    def emit_comp_op_int_le(self, op, arglocs):
        self.emit_int_comp_op(op, arglocs[0], arglocs[1])
        return c.LE

    def emit_comp_op_int_eq(self, op, arglocs):
        self.emit_int_comp_op(op, arglocs[0], arglocs[1])
        return c.EQ

    emit_op_int_lt = gen_comp_op('emit_op_int_lt', c.LT)
    emit_op_int_le = gen_comp_op('emit_op_int_le', c.LE)
    emit_op_int_gt = gen_comp_op('emit_op_int_gt', c.GT)
    emit_op_int_ge = gen_comp_op('emit_op_int_ge', c.GE)
    emit_op_int_eq = gen_comp_op('emit_op_int_eq', c.EQ)
    emit_op_int_ne = gen_comp_op('emit_op_int_ne', c.NE)

    emit_op_uint_lt = gen_comp_op('emit_op_uint_lt', c.LO)
    emit_op_uint_gt = gen_comp_op('emit_op_uint_gt', c.HI)
    emit_op_uint_le = gen_comp_op('emit_op_uint_le', c.LS)
    emit_op_uint_ge = gen_comp_op('emit_op_uint_ge', c.HS)

    def emit_op_int_is_true(self, op, arglocs):
        reg, res = arglocs

        self.mc.CMP_ri(reg.value, 0)
        self.mc.CSET_r_flag(res.value, c.EQ)

    def emit_op_int_is_zero(self, op, arglocs):
        reg, res = arglocs

        self.mc.CMP_ri(reg.value, 0)
        self.mc.CSET_r_flag(res.value, c.NE)

    def emit_op_int_neg(self, op, arglocs):
        reg, res = arglocs
        self.mc.SUB_rr_shifted(res.value, r.xzr.value, reg.value)

    def emit_op_int_invert(self, op, arglocs):
        reg, res = arglocs
        self.mc.MVN_rr(res.value, reg.value)

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
    emit_guard_op_guard_no_overflow = emit_guard_op_guard_true

    def emit_guard_op_guard_false(self, guard_op, fcond, arglocs):
        self._emit_guard(guard_op, c.get_opposite_of(fcond), arglocs)
    emit_guard_op_guard_overflow = emit_guard_op_guard_false

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

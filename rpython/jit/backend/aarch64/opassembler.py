
from rpython.rlib.objectmodel import we_are_translated
from rpython.jit.metainterp.history import (AbstractFailDescr, ConstInt,
                                            INT, FLOAT, REF)
from rpython.jit.backend.aarch64 import registers as r
from rpython.jit.backend.aarch64.codebuilder import OverwritingBuilder
from rpython.jit.backend.aarch64.callbuilder import Aarch64CallBuilder
from rpython.jit.backend.arm import conditions as c, shift
from rpython.jit.backend.aarch64.arch import JITFRAME_FIXED_SIZE, WORD
from rpython.jit.backend.aarch64.locations import imm
from rpython.jit.backend.llsupport.assembler import GuardToken, BaseAssembler
from rpython.jit.backend.llsupport.gcmap import allocate_gcmap
from rpython.jit.backend.llsupport.regalloc import get_scale
from rpython.jit.metainterp.history import TargetToken
from rpython.jit.metainterp.resoperation import rop

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
        self.mc.SMULH_rr(r.ip0.value, reg1.value, reg2.value)
        self.mc.MUL_rr(res.value, reg1.value, reg2.value)
        self.mc.CMP_rr_shifted(r.ip0.value, res.value, 63)

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

    def emit_comp_op_int_gt(self, op, arglocs):
        self.emit_int_comp_op(op, arglocs[0], arglocs[1])
        return c.GT

    def emit_comp_op_int_ge(self, op, arglocs):
        self.emit_int_comp_op(op, arglocs[0], arglocs[1])
        return c.GE

    def emit_comp_op_int_eq(self, op, arglocs):
        self.emit_int_comp_op(op, arglocs[0], arglocs[1])
        return c.EQ

    def emit_comp_op_int_ne(self, op, arglocs):
        self.emit_int_comp_op(op, arglocs[0], arglocs[1])
        return c.NE

    def emit_comp_op_uint_lt(self, op, arglocs):
        self.emit_int_comp_op(op, arglocs[0], arglocs[1])
        return c.LO

    def emit_comp_op_uint_le(self, op, arglocs):
        self.emit_int_comp_op(op, arglocs[0], arglocs[1])
        return c.LS

    def emit_comp_op_uint_gt(self, op, arglocs):
        self.emit_int_comp_op(op, arglocs[0], arglocs[1])
        return c.HI

    def emit_comp_op_uint_ge(self, op, arglocs):
        self.emit_int_comp_op(op, arglocs[0], arglocs[1])
        return c.HS

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

    emit_op_ptr_eq = emit_op_instance_ptr_eq = emit_op_int_eq
    emit_op_ptr_ne = emit_op_instance_ptr_ne = emit_op_int_ne

    def emit_op_int_is_true(self, op, arglocs):
        reg, res = arglocs

        self.mc.CMP_ri(reg.value, 0)
        self.mc.CSET_r_flag(res.value, c.EQ)

    def emit_comp_op_int_is_true(self, op, arglocs):
        self.mc.CMP_ri(arglocs[0].value, 0)
        return c.NE

    def emit_op_int_is_zero(self, op, arglocs):
        reg, res = arglocs

        self.mc.CMP_ri(reg.value, 0)
        self.mc.CSET_r_flag(res.value, c.NE)

    def emit_comp_op_int_is_zero(self, op, arglocs):
        self.mc.CMP_ri(arglocs[0].value, 0)
        return c.EQ

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

    def emit_op_check_memory_error(self, op, arglocs):
        self.propagate_memoryerror_if_reg_is_null(arglocs[0])

    def _genop_same_as(self, op, arglocs):
        argloc, resloc = arglocs
        if argloc is not resloc:
            self.mov_loc_loc(argloc, resloc)

    emit_op_same_as_i = _genop_same_as
    emit_op_same_as_r = _genop_same_as
    emit_op_same_as_f = _genop_same_as
    emit_op_cast_ptr_to_int = _genop_same_as
    emit_op_cast_int_to_ptr = _genop_same_as

    def emit_op_load_from_gc_table(self, op, arglocs):
        res_loc, = arglocs
        index = op.getarg(0).getint()
        self.load_from_gc_table(res_loc.value, index)

    def emit_op_load_effective_address(self, op, arglocs):
        self._gen_address(arglocs[4], arglocs[0], arglocs[1], arglocs[3].value,
                          arglocs[2].value)

   # result = base_loc  + (scaled_loc << scale) + static_offset
    def _gen_address(self, result, base_loc, scaled_loc, scale=0, static_offset=0):
        assert scaled_loc.is_core_reg()
        assert base_loc.is_core_reg()
        if scale > 0:
            self.mc.LSL_ri(r.ip0.value, scaled_loc.value, scale)
            scaled_loc = r.ip0
        else:
            scaled_loc = scaled_loc
        self.mc.ADD_rr(result.value, base_loc.value, scaled_loc.value)
        self.mc.ADD_ri(result.value, result.value, static_offset)

    def emit_op_debug_merge_point(self, op, arglocs):
        pass
    
    emit_op_jit_debug = emit_op_debug_merge_point
    emit_op_keepalive = emit_op_debug_merge_point
    emit_op_enter_portal_frame = emit_op_debug_merge_point
    emit_op_leave_portal_frame = emit_op_debug_merge_point


    # -------------------------------- fields -------------------------------

    def emit_op_gc_store(self, op, arglocs):
        value_loc, base_loc, ofs_loc, size_loc = arglocs
        scale = get_scale(size_loc.value)
        self._write_to_mem(value_loc, base_loc, ofs_loc, scale)

    def _emit_op_gc_load(self, op, arglocs):
        base_loc, ofs_loc, res_loc, nsize_loc = arglocs
        nsize = nsize_loc.value
        signed = (nsize < 0)
        scale = get_scale(abs(nsize))
        self._load_from_mem(res_loc, base_loc, ofs_loc, scale, signed)

    emit_op_gc_load_i = _emit_op_gc_load
    emit_op_gc_load_r = _emit_op_gc_load
    emit_op_gc_load_f = _emit_op_gc_load

    def emit_op_gc_store_indexed(self, op, arglocs):
        value_loc, base_loc, index_loc, size_loc, ofs_loc = arglocs
        assert index_loc.is_core_reg()
        # add the base offset
        if ofs_loc.value > 0:
            self.mc.ADD_ri(r.ip0.value, index_loc.value, ofs_loc.value)
            index_loc = r.ip0
        scale = get_scale(size_loc.value)
        self._write_to_mem(value_loc, base_loc, index_loc, scale)

    def _emit_op_gc_load_indexed(self, op, arglocs):
        res_loc, base_loc, index_loc, nsize_loc, ofs_loc = arglocs
        assert index_loc.is_core_reg()
        nsize = nsize_loc.value
        signed = (nsize < 0)
        # add the base offset
        if ofs_loc.value > 0:
            self.mc.ADD_ri(r.ip0.value, index_loc.value, ofs_loc.value)
            index_loc = r.ip0
        #
        scale = get_scale(abs(nsize))
        self._load_from_mem(res_loc, base_loc, index_loc, scale, signed)

    emit_op_gc_load_indexed_i = _emit_op_gc_load_indexed
    emit_op_gc_load_indexed_r = _emit_op_gc_load_indexed
    emit_op_gc_load_indexed_f = _emit_op_gc_load_indexed

    def _write_to_mem(self, value_loc, base_loc, ofs_loc, scale):
        # Write a value of size '1 << scale' at the address
        # 'base_ofs + ofs_loc'.  Note that 'scale' is not used to scale
        # the offset!
        assert base_loc.is_core_reg()
        if scale == 3:
            # WORD size
            if ofs_loc.is_imm():
                self.mc.STR_ri(value_loc.value, base_loc.value,
                                ofs_loc.value)
            else:
                self.mc.STR_size_rr(3, value_loc.value, base_loc.value,
                                    ofs_loc.value)
        else:
            if ofs_loc.is_imm():
                self.mc.STR_size_ri(scale, value_loc.value, base_loc.value,
                                     ofs_loc.value)
            else:
                self.mc.STR_size_rr(scale, value_loc.value, base_loc.value,
                                     ofs_loc.value)

    def _load_from_mem(self, res_loc, base_loc, ofs_loc, scale,
                                            signed=False):
        # Load a value of '1 << scale' bytes, from the memory location
        # 'base_loc + ofs_loc'.  Note that 'scale' is not used to scale
        # the offset!
        #
        if scale == 3:
            # WORD
            if ofs_loc.is_imm():
                self.mc.LDR_ri(res_loc.value, base_loc.value, ofs_loc.value)
            else:
                self.mc.LDR_rr(res_loc.value, base_loc.value, ofs_loc.value)
            return
        if scale == 2:
            # 32bit int
            if not signed:
                if ofs_loc.is_imm():
                    self.mc.LDR_uint32_ri(res_loc.value, base_loc.value,
                                          ofs_loc.value)
                else:
                    self.mc.LDR_uint32_rr(res_loc.value, base_loc.value,
                                          ofs_loc.value)
            else:
                if ofs_loc.is_imm():
                    self.mc.LDRSW_ri(res_loc.value, base_loc.value,
                                             ofs_loc.value)
                else:
                    self.mc.LDRSW_rr(res_loc.value, base_loc.value,
                                             ofs_loc.value)
            return
        if scale == 1:
            # short
            if not signed:
                if ofs_loc.is_imm():
                    self.mc.LDRH_ri(res_loc.value, base_loc.value, ofs_loc.value)
                else:
                    self.mc.LDRH_rr(res_loc.value, base_loc.value, ofs_loc.value)
            else:
                if ofs_loc.is_imm():
                    self.mc.LDRSH_ri(res_loc.value, base_loc.value, ofs_loc.value)
                else:
                    self.mc.LDRSH_rr(res_loc.value, base_loc.value, ofs_loc.value)
            return
        assert scale == 0
        if not signed:
            if ofs_loc.is_imm():
                self.mc.LDRB_ri(res_loc.value, base_loc.value, ofs_loc.value)
            else:
                self.mc.LDRB_rr(res_loc.value, base_loc.value, ofs_loc.value)
        else:
            if ofs_loc.is_imm():
                self.mc.LDRSB_ri(res_loc.value, base_loc.value, ofs_loc.value)
            else:
                self.mc.LDRSB_rr(res_loc.value, base_loc.value, ofs_loc.value)

    # -------------------------------- guard --------------------------------

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
            if loc.is_stack():
                self.regalloc_mov(loc, r.ip0)
            else:
                assert loc.is_imm()
                self.mc.gen_load_int(r.ip0.value, loc.value)
            loc = r.ip0
        self.mc.CMP_ri(loc.value, 0)

    def emit_op_guard_false(self, op, arglocs):
        self.load_condition_into_cc(arglocs[0])
        self._emit_guard(op, c.EQ, arglocs[1:])
    emit_op_guard_isnull = emit_op_guard_false

    def emit_op_guard_true(self, op, arglocs):
        self.load_condition_into_cc(arglocs[0])
        self._emit_guard(op, c.NE, arglocs[1:])
    emit_op_guard_nonnull = emit_op_guard_true

    def emit_op_guard_value(self, op, arglocs):
        v0 = arglocs[0]
        assert v0.is_core_reg() # can be also a float reg, but later
        v1 = arglocs[1]
        if v1.is_core_reg():
            loc = v1
        elif v1.is_imm():
            self.mc.gen_load_int(r.ip0.value, v1.value)
            loc = r.ip0
        else:
            assert v1.is_stack()
            yyy
        self.mc.CMP_rr(v0.value, loc.value)
        self._emit_guard(op, c.EQ, arglocs[2:])

    def emit_op_guard_class(self, op, arglocs):
        offset = self.cpu.vtable_offset
        assert offset is not None
        self.mc.LDR_ri(r.ip0.value, arglocs[0].value, offset)
        self.mc.gen_load_int(r.ip1.value, arglocs[1].value)
        self.mc.CMP_rr(r.ip0.value, r.ip1.value)
        self._emit_guard(op, c.EQ, arglocs[2:])

    def emit_op_guard_nonnull_class(self, op, arglocs):
        offset = self.cpu.vtable_offset
        assert offset is not None
        # XXX a bit obscure think about a better way
        self.mc.MOVZ_r_u16(r.ip0.value, 1, 0)
        self.mc.MOVZ_r_u16(r.ip1.value, 0, 0)
        self.mc.CMP_ri(arglocs[0].value, 0)
        self.mc.B_ofs_cond(4 * (4 + 2), c.EQ)
        self.mc.LDR_ri(r.ip0.value, arglocs[0].value, offset)
        self.mc.gen_load_int_full(r.ip1.value, arglocs[1].value)
        self.mc.CMP_rr(r.ip0.value, r.ip1.value)
        self._emit_guard(op, c.EQ, arglocs[2:])     

    def emit_op_guard_exception(self, op, arglocs):
        loc, resloc, pos_exc_value, pos_exception = arglocs[:4]
        failargs = arglocs[4:]
        self.mc.gen_load_int(r.ip1.value, pos_exception.value)
        self.mc.LDR_ri(r.ip0.value, r.ip1.value, 0)

        self.mc.CMP_rr(r.ip0.value, loc.value)
        self._emit_guard(op, c.EQ, failargs)
        self._store_and_reset_exception(self.mc, resloc)

    def emit_op_guard_no_exception(self, op, arglocs):
        loc = arglocs[0]
        failargs = arglocs[1:]
        self.mc.LDR_ri(loc.value, loc.value, 0)
        self.mc.CMP_ri(loc.value, 0)
        self._emit_guard(op, c.EQ, failargs)
        # If the previous operation was a COND_CALL, overwrite its conditional
        # jump to jump over this GUARD_NO_EXCEPTION as well, if we can
        #if self._find_nearby_operation(-1).getopnum() == rop.COND_CALL:
        #    XXX
        #    jmp_adr, prev_cond = self.previous_cond_call_jcond
        #    pmc = OverwritingBuilder(self.mc, jmp_adr, WORD)
        #    pmc.B_offs(self.mc.currpos(), prev_cond)

    def emit_op_save_exc_class(self, op, arglocs):
        resloc = arglocs[0]
        self.mc.gen_load_int(r.ip0.value, self.cpu.pos_exception())
        self.load_reg(self.mc, resloc, r.ip0)

    def emit_op_save_exception(self, op, arglocs):
        resloc = arglocs[0]
        self._store_and_reset_exception(self.mc, resloc)

    def emit_op_restore_exception(self, op, arglocs):
        self._restore_exception(self.mc, arglocs[1], arglocs[0])

    def emit_op_cond_call_gc_wb(self, op, arglocs):
        self._write_barrier_fastpath(self.mc, op.getdescr(), arglocs)

    def emit_op_cond_call_gc_wb_array(self, op, arglocs):
        self._write_barrier_fastpath(self.mc, op.getdescr(), arglocs,
                                     array=True)

    def _write_barrier_fastpath(self, mc, descr, arglocs, array=False, is_frame=False):
        # Write code equivalent to write_barrier() in the GC: it checks
        # a flag in the object at arglocs[0], and if set, it calls a
        # helper piece of assembler.  The latter saves registers as needed
        # and call the function remember_young_pointer() from the GC.
        if we_are_translated():
            cls = self.cpu.gc_ll_descr.has_write_barrier_class()
            assert cls is not None and isinstance(descr, cls)
        #
        card_marking = False
        mask = descr.jit_wb_if_flag_singlebyte
        if array and descr.jit_wb_cards_set != 0:
            # assumptions the rest of the function depends on:
            assert (descr.jit_wb_cards_set_byteofs ==
                    descr.jit_wb_if_flag_byteofs)
            assert descr.jit_wb_cards_set_singlebyte == -0x80
            card_marking = True
            mask = descr.jit_wb_if_flag_singlebyte | -0x80
        #
        loc_base = arglocs[0]
        if is_frame:
            assert loc_base is r.fp
        mc.LDRB_ri(r.ip0.value, loc_base.value, descr.jit_wb_if_flag_byteofs)
        mask &= 0xFF
        mc.MOVZ_r_u16(r.ip1.value, mask, 0)
        mc.TST_rr_shift(r.ip0.value, r.ip1.value, 0)
        jz_location = mc.currpos()
        mc.BRK()

        # for cond_call_gc_wb_array, also add another fast path:
        # if GCFLAG_CARDS_SET, then we can just set one bit and be done
        if card_marking:
            mc.MOVZ_r_u16(r.ip1.value, 0x80, 0)
            # GCFLAG_CARDS_SET is in this byte at 0x80
            mc.TST_rr_shift(r.ip0.value, r.ip1.value, 0)

            js_location = mc.currpos()
            mc.BRK()
        else:
            js_location = 0

        # Write only a CALL to the helper prepared in advance, passing it as
        # argument the address of the structure we are writing into
        # (the first argument to COND_CALL_GC_WB).
        helper_num = card_marking
        if is_frame:
            helper_num = 4
        elif self._regalloc is not None and self._regalloc.vfprm.reg_bindings:
            helper_num += 2
        if self.wb_slowpath[helper_num] == 0:    # tests only
            assert not we_are_translated()
            self.cpu.gc_ll_descr.write_barrier_descr = descr
            self._build_wb_slowpath(card_marking,
                                    bool(self._regalloc.vfprm.reg_bindings))
            assert self.wb_slowpath[helper_num] != 0
        #
        if loc_base is not r.x0:
            # push two registers to keep stack aligned
            mc.SUB_ri(r.sp.value, r.sp.value, 2 * WORD)
            mc.STR_ri(r.x0.value, r.sp.value, WORD)
            mc.STR_ri(loc_base.value, r.sp.value, 0)
            mc.MOV_rr(r.x0.value, loc_base.value)
            if is_frame:
                assert loc_base is r.fp
        mc.BL(self.wb_slowpath[helper_num])
        if loc_base is not r.x0:
            mc.LDR_ri(r.x0.value, r.sp.value, WORD)
            mc.LDR_ri(loc_base.value, r.sp.value, 0)
            mc.ADD_ri(r.sp.value, r.sp.value, 2 * WORD)

        if card_marking:
            # The helper ends again with a check of the flag in the object.  So
            # here, we can simply write again a conditional jump, which will be
            # taken if GCFLAG_CARDS_SET is still not set.
            jns_location = mc.currpos()
            mc.BRK()
            #
            # patch the JS above
            offset = mc.currpos() - js_location
            pmc = OverwritingBuilder(mc, js_location, WORD)
            pmc.B_ofs_cond(offset, c.NE)  # We want to jump if the z flag isn't set
            #
            # case GCFLAG_CARDS_SET: emit a few instructions to do
            # directly the card flag setting
            loc_index = arglocs[1]
            assert loc_index.is_core_reg()
            tmp1 = r.ip1
            tmp2 = arglocs[-1]  # the last item is a preallocated tmp
            # lr = byteofs
            s = 3 + descr.jit_wb_card_page_shift
            mc.MVN_rr_shift(r.lr.value, loc_index.value, s, shifttype=shift.LSR)

            # tmp1 = byte_index
            mc.MOVZ_r_u16(r.ip0.value, 7, 0)
            mc.AND_rr_shift(tmp1.value, r.ip0.value, loc_index.value,
                            descr.jit_wb_card_page_shift, shifttype=shift.LSR)

            # set the bit
            mc.MOVZ_r_u16(tmp2.value, 1, 0)
            mc.LDRB_rr(r.ip0.value, loc_base.value, r.lr.value)
            mc.LSL_rr(tmp2.value, tmp2.value, tmp1.value)
            mc.ORR_rr(r.ip0.value, r.ip0.value, tmp2.value)
            mc.STR_size_rr(0, r.ip0.value, loc_base.value, r.lr.value)
            # done
            #
            # patch the JNS above
            offset = mc.currpos() - jns_location
            pmc = OverwritingBuilder(mc, jns_location, WORD)
            pmc.B_ofs_cond(offset, c.EQ)  # We want to jump if the z flag is set

        offset = mc.currpos() - jz_location
        pmc = OverwritingBuilder(mc, jz_location, WORD)
        pmc.B_ofs_cond(offset, c.EQ)

    # ----------------------------- call ------------------------------

    def _genop_call(self, op, arglocs):
        return self._emit_call(op, arglocs)
    emit_op_call_i = _genop_call
    emit_op_call_r = _genop_call
    emit_op_call_f = _genop_call
    emit_op_call_n = _genop_call

    def _emit_call(self, op, arglocs, is_call_release_gil=False):
        # args = [resloc, size, sign, args...]
        from rpython.jit.backend.llsupport.descr import CallDescr

        func_index = 3 + is_call_release_gil
        cb = Aarch64CallBuilder(self, arglocs[func_index],
                                arglocs[func_index+1:], arglocs[0])

        descr = op.getdescr()
        assert isinstance(descr, CallDescr)
        cb.callconv = descr.get_call_conv()
        cb.argtypes = descr.get_arg_types()
        cb.restype  = descr.get_result_type()
        sizeloc = arglocs[1]
        assert sizeloc.is_imm()
        cb.ressize = sizeloc.value
        signloc = arglocs[2]
        assert signloc.is_imm()
        cb.ressign = signloc.value

        if is_call_release_gil:
            saveerrloc = arglocs[3]
            assert saveerrloc.is_imm()
            cb.emit_call_release_gil(saveerrloc.value)
        else:
            effectinfo = descr.get_extra_info()
            if effectinfo is None or effectinfo.check_can_collect():
                cb.emit()
            else:
                cb.emit_no_collect()

    def emit_op_label(self, op, arglocs):
        pass

    def emit_op_jump(self, op, arglocs):
        target_token = op.getdescr()
        assert isinstance(target_token, TargetToken)
        target = target_token._ll_loop_code
        if target_token in self.target_tokens_currently_compiling:
            self.mc.B_ofs(target - self.mc.currpos())
        else:
            self.mc.B(target)

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
            self.push_gcmap(self.mc, gcmap)
        elif self._finish_gcmap:
            # we're returning with a guard_not_forced_2
            gcmap = self._finish_gcmap
            self.push_gcmap(self.mc, gcmap)
        else:
            # note that the 0 here is redundant, but I would rather
            # keep that one and kill all the others
            ofs = self.cpu.get_ofs_of_frame_field('jf_gcmap')
            self.store_reg(self.mc, r.xzr, r.fp, ofs)
        self.mc.MOV_rr(r.x0.value, r.fp.value)
        # exit function
        self.gen_func_epilog()

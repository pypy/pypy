from __future__ import with_statement
from rpython.jit.backend.arm import conditions as c
from rpython.jit.backend.arm import registers as r
from rpython.jit.backend.arm import shift
from rpython.jit.backend.arm.arch import WORD, DOUBLE_WORD, JITFRAME_FIXED_SIZE
from rpython.jit.backend.arm.helper.assembler import (gen_emit_op_by_helper_call,
                                                gen_emit_op_unary_cmp,
                                                gen_emit_guard_unary_cmp,
                                                gen_emit_op_ri,
                                                gen_emit_cmp_op,
                                                gen_emit_cmp_op_guard,
                                                gen_emit_float_op,
                                                gen_emit_float_cmp_op,
                                                gen_emit_float_cmp_op_guard,
                                                gen_emit_unary_float_op,
                                                saved_registers)
from rpython.jit.backend.arm.helper.regalloc import check_imm_arg
from rpython.jit.backend.arm.helper.regalloc import VMEM_imm_size
from rpython.jit.backend.arm.codebuilder import InstrBuilder, OverwritingBuilder
from rpython.jit.backend.arm.jump import remap_frame_layout
from rpython.jit.backend.arm.regalloc import TempBox
from rpython.jit.backend.arm.locations import imm
from rpython.jit.backend.llsupport import symbolic
from rpython.jit.backend.llsupport.gcmap import allocate_gcmap
from rpython.jit.backend.llsupport.descr import InteriorFieldDescr
from rpython.jit.backend.llsupport.assembler import GuardToken, BaseAssembler
from rpython.jit.backend.llsupport.regalloc import get_scale
from rpython.jit.metainterp.history import (Box, AbstractFailDescr,
                                            INT, FLOAT, REF)
from rpython.jit.metainterp.history import TargetToken
from rpython.jit.metainterp.resoperation import rop
from rpython.rlib.objectmodel import we_are_translated
from rpython.rtyper.lltypesystem import rstr, rffi, lltype
from rpython.rtyper.annlowlevel import cast_instance_to_gcref
from rpython.jit.backend.arm import callbuilder
from rpython.rlib.rarithmetic import r_uint


class ArmGuardToken(GuardToken):
    def __init__(self, cpu, gcmap, faildescr, failargs, fail_locs,
                 offset, exc, frame_depth, is_guard_not_invalidated=False,
                 is_guard_not_forced=False, fcond=c.AL):
        GuardToken.__init__(self, cpu, gcmap, faildescr, failargs, fail_locs,
                            exc, frame_depth, is_guard_not_invalidated,
                            is_guard_not_forced)
        self.fcond = fcond
        self.offset = offset


class ResOpAssembler(BaseAssembler):

    def emit_op_int_add(self, op, arglocs, regalloc, fcond):
        return self.int_add_impl(op, arglocs, regalloc, fcond)

    def int_add_impl(self, op, arglocs, regalloc, fcond, flags=False):
        l0, l1, res = arglocs
        if flags:
            s = 1
        else:
            s = 0
        if l0.is_imm():
            self.mc.ADD_ri(res.value, l1.value, imm=l0.value, s=s)
        elif l1.is_imm():
            self.mc.ADD_ri(res.value, l0.value, imm=l1.value, s=s)
        else:
            self.mc.ADD_rr(res.value, l0.value, l1.value, s=1)

        return fcond

    def emit_op_int_sub(self, op, arglocs, regalloc, fcond, flags=False):
        return self.int_sub_impl(op, arglocs, regalloc, fcond)

    def int_sub_impl(self, op, arglocs, regalloc, fcond, flags=False):
        l0, l1, res = arglocs
        if flags:
            s = 1
        else:
            s = 0
        if l0.is_imm():
            value = l0.getint()
            assert value >= 0
            # reverse substract ftw
            self.mc.RSB_ri(res.value, l1.value, value, s=s)
        elif l1.is_imm():
            value = l1.getint()
            assert value >= 0
            self.mc.SUB_ri(res.value, l0.value, value, s=s)
        else:
            self.mc.SUB_rr(res.value, l0.value, l1.value, s=s)

        return fcond

    def emit_op_int_mul(self, op, arglocs, regalloc, fcond):
        reg1, reg2, res = arglocs
        self.mc.MUL(res.value, reg1.value, reg2.value)
        return fcond

    def emit_op_int_force_ge_zero(self, op, arglocs, regalloc, fcond):
        arg, res = arglocs
        self.mc.CMP_ri(arg.value, 0)
        self.mc.MOV_ri(res.value, 0, cond=c.LT)
        self.mc.MOV_rr(res.value, arg.value, cond=c.GE)
        return fcond

    #ref: http://blogs.arm.com/software-enablement/detecting-overflow-from-mul/
    def emit_guard_int_mul_ovf(self, op, guard, arglocs, regalloc, fcond):
        reg1 = arglocs[0]
        reg2 = arglocs[1]
        res = arglocs[2]
        failargs = arglocs[3:]
        self.mc.SMULL(res.value, r.ip.value, reg1.value, reg2.value,
                                                                cond=fcond)
        self.mc.CMP_rr(r.ip.value, res.value, shifttype=shift.ASR,
                                                        imm=31, cond=fcond)

        if guard.getopnum() == rop.GUARD_OVERFLOW:
            fcond = self._emit_guard(guard, failargs, c.NE, save_exc=False)
        elif guard.getopnum() == rop.GUARD_NO_OVERFLOW:
            fcond = self._emit_guard(guard, failargs, c.EQ, save_exc=False)
        else:
            assert 0
        return fcond

    def emit_guard_int_add_ovf(self, op, guard, arglocs, regalloc, fcond):
        self.int_add_impl(op, arglocs[0:3], regalloc, fcond, flags=True)
        self._emit_guard_overflow(guard, arglocs[3:], fcond)
        return fcond

    def emit_guard_int_sub_ovf(self, op, guard, arglocs, regalloc, fcond):
        self.int_sub_impl(op, arglocs[0:3], regalloc, fcond, flags=True)
        self._emit_guard_overflow(guard, arglocs[3:], fcond)
        return fcond

    emit_op_int_floordiv = gen_emit_op_by_helper_call('int_floordiv', 'DIV')
    emit_op_int_mod = gen_emit_op_by_helper_call('int_mod', 'MOD')
    emit_op_uint_floordiv = gen_emit_op_by_helper_call('uint_floordiv', 'UDIV')

    emit_op_int_and = gen_emit_op_ri('int_and', 'AND')
    emit_op_int_or = gen_emit_op_ri('int_or', 'ORR')
    emit_op_int_xor = gen_emit_op_ri('int_xor', 'EOR')
    emit_op_int_lshift = gen_emit_op_ri('int_lshift', 'LSL')
    emit_op_int_rshift = gen_emit_op_ri('int_rshift', 'ASR')
    emit_op_uint_rshift = gen_emit_op_ri('uint_rshift', 'LSR')

    emit_op_int_lt = gen_emit_cmp_op('int_lt', c.LT)
    emit_op_int_le = gen_emit_cmp_op('int_le', c.LE)
    emit_op_int_eq = gen_emit_cmp_op('int_eq', c.EQ)
    emit_op_int_ne = gen_emit_cmp_op('int_ne', c.NE)
    emit_op_int_gt = gen_emit_cmp_op('int_gt', c.GT)
    emit_op_int_ge = gen_emit_cmp_op('int_ge', c.GE)

    emit_guard_int_lt = gen_emit_cmp_op_guard('int_lt', c.LT)
    emit_guard_int_le = gen_emit_cmp_op_guard('int_le', c.LE)
    emit_guard_int_eq = gen_emit_cmp_op_guard('int_eq', c.EQ)
    emit_guard_int_ne = gen_emit_cmp_op_guard('int_ne', c.NE)
    emit_guard_int_gt = gen_emit_cmp_op_guard('int_gt', c.GT)
    emit_guard_int_ge = gen_emit_cmp_op_guard('int_ge', c.GE)

    emit_op_uint_le = gen_emit_cmp_op('uint_le', c.LS)
    emit_op_uint_gt = gen_emit_cmp_op('uint_gt', c.HI)
    emit_op_uint_lt = gen_emit_cmp_op('uint_lt', c.LO)
    emit_op_uint_ge = gen_emit_cmp_op('uint_ge', c.HS)

    emit_guard_uint_le = gen_emit_cmp_op_guard('uint_le', c.LS)
    emit_guard_uint_gt = gen_emit_cmp_op_guard('uint_gt', c.HI)
    emit_guard_uint_lt = gen_emit_cmp_op_guard('uint_lt', c.LO)
    emit_guard_uint_ge = gen_emit_cmp_op_guard('uint_ge', c.HS)

    emit_op_ptr_eq = emit_op_instance_ptr_eq = emit_op_int_eq
    emit_op_ptr_ne = emit_op_instance_ptr_ne = emit_op_int_ne
    emit_guard_ptr_eq = emit_guard_instance_ptr_eq = emit_guard_int_eq
    emit_guard_ptr_ne = emit_guard_instance_ptr_ne = emit_guard_int_ne

    emit_op_int_add_ovf = emit_op_int_add
    emit_op_int_sub_ovf = emit_op_int_sub

    emit_op_int_is_true = gen_emit_op_unary_cmp('int_is_true', c.NE)
    emit_op_int_is_zero = gen_emit_op_unary_cmp('int_is_zero', c.EQ)

    emit_guard_int_is_true = gen_emit_guard_unary_cmp('int_is_true', c.NE)
    emit_guard_int_is_zero = gen_emit_guard_unary_cmp('int_is_zero', c.EQ)

    def emit_op_int_invert(self, op, arglocs, regalloc, fcond):
        reg, res = arglocs

        self.mc.MVN_rr(res.value, reg.value)
        return fcond

    def emit_op_int_neg(self, op, arglocs, regalloc, fcond):
        l0, resloc = arglocs
        self.mc.RSB_ri(resloc.value, l0.value, imm=0)
        return fcond

    def build_guard_token(self, op, frame_depth, arglocs, offset, fcond, save_exc,
                                    is_guard_not_invalidated=False,
                                    is_guard_not_forced=False):
        assert isinstance(save_exc, bool)
        assert isinstance(fcond, int)
        descr = op.getdescr()
        assert isinstance(descr, AbstractFailDescr)

        gcmap = allocate_gcmap(self, frame_depth, JITFRAME_FIXED_SIZE)
        token = ArmGuardToken(self.cpu, gcmap,
                                    descr,
                                    failargs=op.getfailargs(),
                                    fail_locs=arglocs,
                                    offset=offset,
                                    exc=save_exc,
                                    frame_depth=frame_depth,
                                    is_guard_not_invalidated=is_guard_not_invalidated,
                                    is_guard_not_forced=is_guard_not_forced,
                                    fcond=fcond)
        return token

    def _emit_guard(self, op, arglocs, fcond, save_exc,
                                    is_guard_not_invalidated=False,
                                    is_guard_not_forced=False):
        pos = self.mc.currpos()
        token = self.build_guard_token(op, arglocs[0].value, arglocs[1:], pos, fcond, save_exc,
                                        is_guard_not_invalidated,
                                        is_guard_not_forced)
        self.pending_guards.append(token)
        # For all guards that are not GUARD_NOT_INVALIDATED we emit a
        # breakpoint to ensure the location is patched correctly. In the case
        # of GUARD_NOT_INVALIDATED we use just a NOP, because it is only
        # eventually patched at a later point.
        if is_guard_not_invalidated:
            self.mc.NOP()
        else:
            self.mc.BKPT()
        return c.AL

    def _emit_guard_overflow(self, guard, failargs, fcond):
        if guard.getopnum() == rop.GUARD_OVERFLOW:
            fcond = self._emit_guard(guard, failargs, c.VS, save_exc=False)
        elif guard.getopnum() == rop.GUARD_NO_OVERFLOW:
            fcond = self._emit_guard(guard, failargs, c.VC, save_exc=False)
        else:
            assert 0
        return fcond

    def emit_op_guard_true(self, op, arglocs, regalloc, fcond):
        l0 = arglocs[0]
        failargs = arglocs[1:]
        self.mc.CMP_ri(l0.value, 0)
        fcond = self._emit_guard(op, failargs, c.NE, save_exc=False)
        return fcond

    def emit_op_guard_false(self, op, arglocs, regalloc, fcond):
        l0 = arglocs[0]
        failargs = arglocs[1:]
        self.mc.CMP_ri(l0.value, 0)
        fcond = self._emit_guard(op, failargs, c.EQ, save_exc=False)
        return fcond

    def emit_op_guard_value(self, op, arglocs, regalloc, fcond):
        l0 = arglocs[0]
        l1 = arglocs[1]
        failargs = arglocs[2:]

        if l0.is_core_reg():
            if l1.is_imm():
                self.mc.CMP_ri(l0.value, l1.getint())
            else:
                self.mc.CMP_rr(l0.value, l1.value)
        elif l0.is_vfp_reg():
            assert l1.is_vfp_reg()
            self.mc.VCMP(l0.value, l1.value)
            self.mc.VMRS(cond=fcond)
        fcond = self._emit_guard(op, failargs, c.EQ, save_exc=False)
        return fcond

    emit_op_guard_nonnull = emit_op_guard_true
    emit_op_guard_isnull = emit_op_guard_false

    def emit_op_guard_no_overflow(self, op, arglocs, regalloc, fcond):
        return self._emit_guard(op, arglocs, c.VC, save_exc=False)

    def emit_op_guard_overflow(self, op, arglocs, regalloc, fcond):
        return self._emit_guard(op, arglocs, c.VS, save_exc=False)

    def emit_op_guard_class(self, op, arglocs, regalloc, fcond):
        self._cmp_guard_class(op, arglocs, regalloc, fcond)
        self._emit_guard(op, arglocs[3:], c.EQ, save_exc=False)
        return fcond

    def emit_op_guard_nonnull_class(self, op, arglocs, regalloc, fcond):
        self.mc.CMP_ri(arglocs[0].value, 1)
        self._cmp_guard_class(op, arglocs, regalloc, c.HS)
        self._emit_guard(op, arglocs[3:], c.EQ, save_exc=False)
        return fcond

    def _cmp_guard_class(self, op, locs, regalloc, fcond):
        offset = locs[2]
        if offset is not None:
            self.mc.LDR_ri(r.ip.value, locs[0].value, offset.value, cond=fcond)
            self.mc.CMP_rr(r.ip.value, locs[1].value, cond=fcond)
        else:
            typeid = locs[1]
            self.mc.LDRH_ri(r.ip.value, locs[0].value, cond=fcond)
            if typeid.is_imm():
                self.mc.CMP_ri(r.ip.value, typeid.value, cond=fcond)
            else:
                self.mc.CMP_rr(r.ip.value, typeid.value, cond=fcond)

    def emit_op_guard_not_invalidated(self, op, locs, regalloc, fcond):
        return self._emit_guard(op, locs, fcond, save_exc=False,
                                            is_guard_not_invalidated=True)

    def emit_op_label(self, op, arglocs, regalloc, fcond):
        self._check_frame_depth_debug(self.mc)
        return fcond

    def cond_call(self, op, gcmap, cond_loc, call_loc, fcond):
        assert call_loc is r.r4
        self.mc.TST_rr(cond_loc.value, cond_loc.value)
        jmp_adr = self.mc.currpos()
        self.mc.BKPT()  # patched later
        #
        self.push_gcmap(self.mc, gcmap, store=True)
        #
        callee_only = False
        floats = False
        if self._regalloc is not None:
            for reg in self._regalloc.rm.reg_bindings.values():
                if reg not in self._regalloc.rm.save_around_call_regs:
                    break
            else:
                callee_only = True
            if self._regalloc.vfprm.reg_bindings:
                floats = True
        cond_call_adr = self.cond_call_slowpath[floats * 2 + callee_only]
        self.mc.BL(cond_call_adr)
        self.pop_gcmap(self.mc)
        # never any result value
        pmc = OverwritingBuilder(self.mc, jmp_adr, WORD)
        pmc.B_offs(self.mc.currpos(), c.EQ)  # equivalent to 0 as result of TST above
        return fcond

    def emit_op_jump(self, op, arglocs, regalloc, fcond):
        target_token = op.getdescr()
        assert isinstance(target_token, TargetToken)
        target = target_token._ll_loop_code
        assert fcond == c.AL
        if target_token in self.target_tokens_currently_compiling:
            self.mc.B_offs(target, fcond)
        else:
            self.mc.B(target, fcond)
        return fcond

    def emit_op_finish(self, op, arglocs, regalloc, fcond):
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        if len(arglocs) == 2:
            [return_val, fail_descr_loc] = arglocs
            self.store_reg(self.mc, return_val, r.fp, base_ofs)
        else:
            [fail_descr_loc] = arglocs
        ofs = self.cpu.get_ofs_of_frame_field('jf_descr')

        self.mc.gen_load_int(r.ip.value, fail_descr_loc.value)
        # XXX self.mov(fail_descr_loc, RawStackLoc(ofs))
        self.store_reg(self.mc, r.ip, r.fp, ofs, helper=r.lr)
        if op.numargs() > 0 and op.getarg(0).type == REF:
            if self._finish_gcmap:
                # we're returning with a guard_not_forced_2, and
                # additionally we need to say that r0 contains
                # a reference too:
                self._finish_gcmap[0] |= r_uint(0)
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
            self.mc.gen_load_int(r.ip.value, 0)
            self.store_reg(self.mc, r.ip, r.fp, ofs)
        self.mc.MOV_rr(r.r0.value, r.fp.value)
        # exit function
        self.gen_func_epilog()
        return fcond

    def emit_op_call(self, op, arglocs, regalloc, fcond):
        return self._emit_call(op, arglocs, fcond=fcond)

    def _emit_call(self, op, arglocs, is_call_release_gil=False, fcond=c.AL):
        # args = [resloc, size, sign, args...]
        from rpython.jit.backend.llsupport.descr import CallDescr

        cb = callbuilder.get_callbuilder(self.cpu, self, arglocs[3], arglocs[4:], arglocs[0])

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
            cb.emit_call_release_gil()
        else:
            cb.emit()
        return fcond

    def emit_op_same_as(self, op, arglocs, regalloc, fcond):
        argloc, resloc = arglocs
        if argloc is not resloc:
            self.mov_loc_loc(argloc, resloc)
        return fcond

    emit_op_cast_ptr_to_int = emit_op_same_as
    emit_op_cast_int_to_ptr = emit_op_same_as

    def emit_op_guard_no_exception(self, op, arglocs, regalloc, fcond):
        loc = arglocs[0]
        failargs = arglocs[1:]
        self.mc.LDR_ri(loc.value, loc.value)
        self.mc.CMP_ri(loc.value, 0)
        cond = self._emit_guard(op, failargs, c.EQ, save_exc=True)
        return cond

    def emit_op_guard_exception(self, op, arglocs, regalloc, fcond):
        loc, loc1, resloc, pos_exc_value, pos_exception = arglocs[:5]
        failargs = arglocs[5:]
        self.mc.gen_load_int(loc1.value, pos_exception.value)
        self.mc.LDR_ri(r.ip.value, loc1.value)

        self.mc.CMP_rr(r.ip.value, loc.value)
        self._emit_guard(op, failargs, c.EQ, save_exc=True)
        self._store_and_reset_exception(self.mc, resloc)
        return fcond

    def emit_op_debug_merge_point(self, op, arglocs, regalloc, fcond):
        return fcond
    emit_op_jit_debug = emit_op_debug_merge_point
    emit_op_keepalive = emit_op_debug_merge_point

    def emit_op_cond_call_gc_wb(self, op, arglocs, regalloc, fcond):
        self._write_barrier_fastpath(self.mc, op.getdescr(), arglocs, fcond)
        return fcond

    def emit_op_cond_call_gc_wb_array(self, op, arglocs, regalloc, fcond):
        self._write_barrier_fastpath(self.mc, op.getdescr(), arglocs,
                                                        fcond, array=True)
        return fcond

    def _write_barrier_fastpath(self, mc, descr, arglocs, fcond=c.AL, array=False,
                                                            is_frame=False):
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
        mc.LDRB_ri(r.ip.value, loc_base.value,
                                    imm=descr.jit_wb_if_flag_byteofs)
        mask &= 0xFF
        mc.TST_ri(r.ip.value, imm=mask)
        jz_location = mc.currpos()
        mc.BKPT()

        # for cond_call_gc_wb_array, also add another fast path:
        # if GCFLAG_CARDS_SET, then we can just set one bit and be done
        if card_marking:
            # GCFLAG_CARDS_SET is in this byte at 0x80
            mc.TST_ri(r.ip.value, imm=0x80)

            js_location = mc.currpos()
            mc.BKPT()
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
        if loc_base is not r.r0:
            # push two registers to keep stack aligned
            mc.PUSH([r.r0.value, loc_base.value])
            mc.MOV_rr(r.r0.value, loc_base.value)
            if is_frame:
                assert loc_base is r.fp
        mc.BL(self.wb_slowpath[helper_num])
        if loc_base is not r.r0:
            mc.POP([r.r0.value, loc_base.value])

        if card_marking:
            # The helper ends again with a check of the flag in the object.  So
            # here, we can simply write again a conditional jump, which will be
            # taken if GCFLAG_CARDS_SET is still not set.
            jns_location = mc.currpos()
            mc.BKPT()
            #
            # patch the JS above
            offset = mc.currpos()
            pmc = OverwritingBuilder(mc, js_location, WORD)
            pmc.B_offs(offset, c.NE)  # We want to jump if the z flag isn't set
            #
            # case GCFLAG_CARDS_SET: emit a few instructions to do
            # directly the card flag setting
            loc_index = arglocs[1]
            assert loc_index.is_core_reg()
            # must save the register loc_index before it is mutated
            mc.PUSH([loc_index.value])
            tmp1 = loc_index
            tmp2 = arglocs[-1]  # the last item is a preallocated tmp
            # lr = byteofs
            s = 3 + descr.jit_wb_card_page_shift
            mc.MVN_rr(r.lr.value, loc_index.value,
                                       imm=s, shifttype=shift.LSR)

            # tmp1 = byte_index
            mc.MOV_ri(r.ip.value, imm=7)
            mc.AND_rr(tmp1.value, r.ip.value, loc_index.value,
            imm=descr.jit_wb_card_page_shift, shifttype=shift.LSR)

            # set the bit
            mc.MOV_ri(tmp2.value, imm=1)
            mc.LDRB_rr(r.ip.value, loc_base.value, r.lr.value)
            mc.ORR_rr_sr(r.ip.value, r.ip.value, tmp2.value,
                                          tmp1.value, shifttype=shift.LSL)
            mc.STRB_rr(r.ip.value, loc_base.value, r.lr.value)
            # done
            mc.POP([loc_index.value])
            #
            #
            # patch the JNS above
            offset = mc.currpos()
            pmc = OverwritingBuilder(mc, jns_location, WORD)
            pmc.B_offs(offset, c.EQ)  # We want to jump if the z flag is set

        offset = mc.currpos()
        pmc = OverwritingBuilder(mc, jz_location, WORD)
        pmc.B_offs(offset, c.EQ)
        return fcond

    def emit_op_setfield_gc(self, op, arglocs, regalloc, fcond):
        value_loc, base_loc, ofs, size = arglocs
        scale = get_scale(size.value)
        self._write_to_mem(value_loc, base_loc,
                                ofs, imm(scale), fcond)
        return fcond

    emit_op_setfield_raw = emit_op_setfield_gc

    def emit_op_getfield_gc(self, op, arglocs, regalloc, fcond):
        base_loc, ofs, res, size = arglocs
        signed = op.getdescr().is_field_signed()
        scale = get_scale(size.value)
        self._load_from_mem(res, base_loc, ofs, imm(scale), signed, fcond)
        return fcond

    emit_op_getfield_raw = emit_op_getfield_gc
    emit_op_getfield_raw_pure = emit_op_getfield_gc
    emit_op_getfield_gc_pure = emit_op_getfield_gc

    def emit_op_increment_debug_counter(self, op, arglocs, regalloc, fcond):
        base_loc, value_loc = arglocs
        self.mc.LDR_ri(value_loc.value, base_loc.value, 0, cond=fcond)
        self.mc.ADD_ri(value_loc.value, value_loc.value, 1, cond=fcond)
        self.mc.STR_ri(value_loc.value, base_loc.value, 0, cond=fcond)
        return fcond

    def emit_op_getinteriorfield_gc(self, op, arglocs, regalloc, fcond):
        (base_loc, index_loc, res_loc,
            ofs_loc, ofs, itemsize, fieldsize) = arglocs
        scale = get_scale(fieldsize.value)
        tmploc, save = self.get_tmp_reg([base_loc, ofs_loc])
        assert not save
        self.mc.gen_load_int(tmploc.value, itemsize.value)
        self.mc.MUL(tmploc.value, index_loc.value, tmploc.value)
        descr = op.getdescr()
        assert isinstance(descr, InteriorFieldDescr)
        signed = descr.fielddescr.is_field_signed()
        if ofs.value > 0:
            if ofs_loc.is_imm():
                self.mc.ADD_ri(tmploc.value, tmploc.value, ofs_loc.value)
            else:
                self.mc.ADD_rr(tmploc.value, tmploc.value, ofs_loc.value)
        ofs_loc = tmploc
        self._load_from_mem(res_loc, base_loc, ofs_loc,
                                imm(scale), signed, fcond)
        return fcond

    def emit_op_setinteriorfield_gc(self, op, arglocs, regalloc, fcond):
        (base_loc, index_loc, value_loc,
            ofs_loc, ofs, itemsize, fieldsize) = arglocs
        scale = get_scale(fieldsize.value)
        tmploc, save = self.get_tmp_reg([base_loc, index_loc, value_loc, ofs_loc])
        assert not save
        self.mc.gen_load_int(tmploc.value, itemsize.value)
        self.mc.MUL(tmploc.value, index_loc.value, tmploc.value)
        if ofs.value > 0:
            if ofs_loc.is_imm():
                self.mc.ADD_ri(tmploc.value, tmploc.value, ofs_loc.value)
            else:
                self.mc.ADD_rr(tmploc.value, tmploc.value, ofs_loc.value)
        self._write_to_mem(value_loc, base_loc, tmploc, imm(scale), fcond)
        return fcond
    emit_op_setinteriorfield_raw = emit_op_setinteriorfield_gc

    def emit_op_arraylen_gc(self, op, arglocs, regalloc, fcond):
        res, base_loc, ofs = arglocs
        self.load_reg(self.mc, res, base_loc, ofs.value)
        return fcond

    def emit_op_setarrayitem_gc(self, op, arglocs, regalloc, fcond):
        value_loc, base_loc, ofs_loc, scale, ofs = arglocs
        assert ofs_loc.is_core_reg()
        if scale.value > 0:
            self.mc.LSL_ri(r.ip.value, ofs_loc.value, scale.value)
            ofs_loc = r.ip

        # add the base offset
        if ofs.value > 0:
            self.mc.ADD_ri(r.ip.value, ofs_loc.value, imm=ofs.value)
            ofs_loc = r.ip
        self._write_to_mem(value_loc, base_loc, ofs_loc, scale, fcond)
        return fcond

    def _write_to_mem(self, value_loc, base_loc, ofs_loc, scale, fcond=c.AL):
        if scale.value == 3:
            assert value_loc.is_vfp_reg()
            # vstr only supports imm offsets
            # so if the ofset is too large we add it to the base and use an
            # offset of 0
            if ofs_loc.is_core_reg():
                tmploc, save = self.get_tmp_reg([value_loc, base_loc, ofs_loc])
                assert not save
                self.mc.ADD_rr(tmploc.value, base_loc.value, ofs_loc.value)
                base_loc = tmploc
                ofs_loc = imm(0)
            else:
                assert ofs_loc.is_imm()
                assert ofs_loc.value % 4 == 0
            self.mc.VSTR(value_loc.value, base_loc.value, ofs_loc.value)
        elif scale.value == 2:
            if ofs_loc.is_imm():
                self.mc.STR_ri(value_loc.value, base_loc.value,
                                ofs_loc.value, cond=fcond)
            else:
                self.mc.STR_rr(value_loc.value, base_loc.value,
                                ofs_loc.value, cond=fcond)
        elif scale.value == 1:
            if ofs_loc.is_imm():
                self.mc.STRH_ri(value_loc.value, base_loc.value,
                                ofs_loc.value, cond=fcond)
            else:
                self.mc.STRH_rr(value_loc.value, base_loc.value,
                                ofs_loc.value, cond=fcond)
        elif scale.value == 0:
            if ofs_loc.is_imm():
                self.mc.STRB_ri(value_loc.value, base_loc.value,
                                ofs_loc.value, cond=fcond)
            else:
                self.mc.STRB_rr(value_loc.value, base_loc.value,
                                ofs_loc.value, cond=fcond)
        else:
            assert 0

    emit_op_setarrayitem_raw = emit_op_setarrayitem_gc

    def emit_op_raw_store(self, op, arglocs, regalloc, fcond):
        value_loc, base_loc, ofs_loc, scale, ofs = arglocs
        assert ofs_loc.is_core_reg()
        self._write_to_mem(value_loc, base_loc, ofs_loc, scale, fcond)
        return fcond

    def emit_op_getarrayitem_gc(self, op, arglocs, regalloc, fcond):
        res_loc, base_loc, ofs_loc, scale, ofs = arglocs
        assert ofs_loc.is_core_reg()
        signed = op.getdescr().is_item_signed()

        # scale the offset as required
        if scale.value > 0:
            self.mc.LSL_ri(r.ip.value, ofs_loc.value, scale.value)
            ofs_loc = r.ip
        # add the base offset
        if ofs.value > 0:
            self.mc.ADD_ri(r.ip.value, ofs_loc.value, imm=ofs.value)
            ofs_loc = r.ip
        #
        self._load_from_mem(res_loc, base_loc, ofs_loc, scale, signed, fcond)
        return fcond

    def _load_from_mem(self, res_loc, base_loc, ofs_loc, scale,
                                            signed=False, fcond=c.AL):
        if scale.value == 3:
            assert res_loc.is_vfp_reg()
            # vldr only supports imm offsets
            # if the offset is in a register we add it to the base and use a
            # tmp reg
            if ofs_loc.is_core_reg():
                tmploc, save = self.get_tmp_reg([base_loc, ofs_loc])
                assert not save
                self.mc.ADD_rr(tmploc.value, base_loc.value, ofs_loc.value)
                base_loc = tmploc
                ofs_loc = imm(0)
            else:
                assert ofs_loc.is_imm()
                assert ofs_loc.value % 4 == 0
            self.mc.VLDR(res_loc.value, base_loc.value, ofs_loc.value, cond=fcond)
        elif scale.value == 2:
            if ofs_loc.is_imm():
                self.mc.LDR_ri(res_loc.value, base_loc.value,
                                ofs_loc.value, cond=fcond)
            else:
                self.mc.LDR_rr(res_loc.value, base_loc.value,
                                ofs_loc.value, cond=fcond)
        elif scale.value == 1:
            if ofs_loc.is_imm():
                if signed:
                    self.mc.LDRSH_ri(res_loc.value, base_loc.value,
                                        ofs_loc.value, cond=fcond)
                else:
                    self.mc.LDRH_ri(res_loc.value, base_loc.value,
                                        ofs_loc.value, cond=fcond)
            else:
                if signed:
                    self.mc.LDRSH_rr(res_loc.value, base_loc.value,
                                        ofs_loc.value, cond=fcond)
                else:
                    self.mc.LDRH_rr(res_loc.value, base_loc.value,
                                        ofs_loc.value, cond=fcond)
        elif scale.value == 0:
            if ofs_loc.is_imm():
                if signed:
                    self.mc.LDRSB_ri(res_loc.value, base_loc.value,
                                        ofs_loc.value, cond=fcond)
                else:
                    self.mc.LDRB_ri(res_loc.value, base_loc.value,
                                        ofs_loc.value, cond=fcond)
            else:
                if signed:
                    self.mc.LDRSB_rr(res_loc.value, base_loc.value,
                                        ofs_loc.value, cond=fcond)
                else:
                    self.mc.LDRB_rr(res_loc.value, base_loc.value,
                                        ofs_loc.value, cond=fcond)
        else:
            assert 0

    emit_op_getarrayitem_raw = emit_op_getarrayitem_gc
    emit_op_getarrayitem_gc_pure = emit_op_getarrayitem_gc

    def emit_op_raw_load(self, op, arglocs, regalloc, fcond):
        res_loc, base_loc, ofs_loc, scale, ofs = arglocs
        assert ofs_loc.is_core_reg()
        # no base offset
        assert ofs.value == 0
        signed = op.getdescr().is_item_signed()
        self._load_from_mem(res_loc, base_loc, ofs_loc, scale, signed, fcond)
        return fcond

    def emit_op_strlen(self, op, arglocs, regalloc, fcond):
        l0, l1, res = arglocs
        if l1.is_imm():
            self.mc.LDR_ri(res.value, l0.value, l1.getint(), cond=fcond)
        else:
            self.mc.LDR_rr(res.value, l0.value, l1.value, cond=fcond)
        return fcond

    def emit_op_strgetitem(self, op, arglocs, regalloc, fcond):
        res, base_loc, ofs_loc, basesize = arglocs
        if ofs_loc.is_imm():
            self.mc.ADD_ri(r.ip.value, base_loc.value, ofs_loc.getint(),
                                                                    cond=fcond)
        else:
            self.mc.ADD_rr(r.ip.value, base_loc.value, ofs_loc.value,
                                                                    cond=fcond)

        self.mc.LDRB_ri(res.value, r.ip.value, basesize.value, cond=fcond)
        return fcond

    def emit_op_strsetitem(self, op, arglocs, regalloc, fcond):
        value_loc, base_loc, ofs_loc, basesize = arglocs
        if ofs_loc.is_imm():
            self.mc.ADD_ri(r.ip.value, base_loc.value, ofs_loc.getint(),
                                                            cond=fcond)
        else:
            self.mc.ADD_rr(r.ip.value, base_loc.value, ofs_loc.value,
                                                            cond=fcond)

        self.mc.STRB_ri(value_loc.value, r.ip.value, basesize.value,
                                                            cond=fcond)
        return fcond

    #from ../x86/regalloc.py:928 ff.
    def emit_op_copystrcontent(self, op, arglocs, regalloc, fcond):
        assert len(arglocs) == 0
        self._emit_copystrcontent(op, regalloc, fcond, is_unicode=False)
        return fcond

    def emit_op_copyunicodecontent(self, op, arglocs, regalloc, fcond):
        assert len(arglocs) == 0
        self._emit_copystrcontent(op, regalloc, fcond, is_unicode=True)
        return fcond

    def _emit_copystrcontent(self, op, regalloc, fcond, is_unicode):
        # compute the source address
        args = op.getarglist()
        base_loc = regalloc.rm.make_sure_var_in_reg(args[0], args)
        ofs_loc = regalloc.rm.make_sure_var_in_reg(args[2], args)
        assert args[0] is not args[1]    # forbidden case of aliasing
        srcaddr_box = TempBox()
        forbidden_vars = [args[1], args[3], args[4], srcaddr_box]
        srcaddr_loc = regalloc.rm.force_allocate_reg(srcaddr_box, forbidden_vars)
        self._gen_address_inside_string(base_loc, ofs_loc, srcaddr_loc,
                                        is_unicode=is_unicode)
        # compute the destination address
        base_loc = regalloc.rm.make_sure_var_in_reg(args[1], forbidden_vars)
        ofs_loc = regalloc.rm.make_sure_var_in_reg(args[3], forbidden_vars)
        forbidden_vars = [args[4], srcaddr_box]
        dstaddr_box = TempBox()
        dstaddr_loc = regalloc.rm.force_allocate_reg(dstaddr_box, forbidden_vars)
        self._gen_address_inside_string(base_loc, ofs_loc, dstaddr_loc,
                                        is_unicode=is_unicode)
        # compute the length in bytes
        length_box = args[4]
        length_loc = regalloc.loc(length_box)
        if is_unicode:
            forbidden_vars = [srcaddr_box, dstaddr_box]
            bytes_box = TempBox()
            bytes_loc = regalloc.rm.force_allocate_reg(bytes_box, forbidden_vars)
            scale = self._get_unicode_item_scale()
            if not length_loc.is_core_reg():
                self.regalloc_mov(length_loc, bytes_loc)
                length_loc = bytes_loc
            assert length_loc.is_core_reg()
            self.mc.MOV_ri(r.ip.value, 1 << scale)
            self.mc.MUL(bytes_loc.value, r.ip.value, length_loc.value)
            length_box = bytes_box
            length_loc = bytes_loc
        # call memcpy()
        regalloc.before_call()
        self.simple_call_no_collect(imm(self.memcpy_addr),
                                  [dstaddr_loc, srcaddr_loc, length_loc])
        regalloc.rm.possibly_free_var(length_box)
        regalloc.rm.possibly_free_var(dstaddr_box)
        regalloc.rm.possibly_free_var(srcaddr_box)

    def _gen_address_inside_string(self, baseloc, ofsloc, resloc, is_unicode):
        if is_unicode:
            ofs_items, _, _ = symbolic.get_array_token(rstr.UNICODE,
                                              self.cpu.translate_support_code)
            scale = self._get_unicode_item_scale()
        else:
            ofs_items, itemsize, _ = symbolic.get_array_token(rstr.STR,
                                              self.cpu.translate_support_code)
            assert itemsize == 1
            scale = 0
        self._gen_address(resloc, baseloc, ofsloc, scale, ofs_items)

   # result = base_loc  + (scaled_loc << scale) + static_offset
    def _gen_address(self, result, base_loc, scaled_loc, scale=0, static_offset=0):
        assert scaled_loc.is_core_reg()
        assert base_loc.is_core_reg()
        assert check_imm_arg(scale)
        assert check_imm_arg(static_offset)
        if scale > 0:
            self.mc.LSL_ri(r.ip.value, scaled_loc.value, scale)
            scaled_loc = r.ip
        else:
            scaled_loc = scaled_loc
        self.mc.ADD_rr(result.value, base_loc.value, scaled_loc.value)
        self.mc.ADD_ri(result.value, result.value, static_offset)

    def _get_unicode_item_scale(self):
        _, itemsize, _ = symbolic.get_array_token(rstr.UNICODE,
                                              self.cpu.translate_support_code)
        if itemsize == 4:
            return 2
        elif itemsize == 2:
            return 1
        else:
            raise AssertionError("bad unicode item size")

    emit_op_unicodelen = emit_op_strlen

    def emit_op_unicodegetitem(self, op, arglocs, regalloc, fcond):
        res, base_loc, ofs_loc, scale, basesize, itemsize = arglocs
        self.mc.ADD_rr(r.ip.value, base_loc.value, ofs_loc.value, cond=fcond,
                                        imm=scale.value, shifttype=shift.LSL)
        if scale.value == 2:
            self.mc.LDR_ri(res.value, r.ip.value, basesize.value, cond=fcond)
        elif scale.value == 1:
            self.mc.LDRH_ri(res.value, r.ip.value, basesize.value, cond=fcond)
        else:
            assert 0, itemsize.value
        return fcond

    def emit_op_unicodesetitem(self, op, arglocs, regalloc, fcond):
        value_loc, base_loc, ofs_loc, scale, basesize, itemsize = arglocs
        self.mc.ADD_rr(r.ip.value, base_loc.value, ofs_loc.value, cond=fcond,
                                        imm=scale.value, shifttype=shift.LSL)
        if scale.value == 2:
            self.mc.STR_ri(value_loc.value, r.ip.value, basesize.value,
                                                                    cond=fcond)
        elif scale.value == 1:
            self.mc.STRH_ri(value_loc.value, r.ip.value, basesize.value,
                                                                    cond=fcond)
        else:
            assert 0, itemsize.value

        return fcond

    def store_force_descr(self, op, fail_locs, frame_depth):
        pos = self.mc.currpos()
        guard_token = self.build_guard_token(op, frame_depth, fail_locs, pos, c.AL, True, False, True)
        #self.pending_guards.append(guard_token)
        self._finish_gcmap = guard_token.gcmap
        self._store_force_index(op)
        self.store_info_on_descr(pos, guard_token)

    def emit_op_force_token(self, op, arglocs, regalloc, fcond):
        # XXX kill me
        res_loc = arglocs[0]
        self.mc.MOV_rr(res_loc.value, r.fp.value)
        return fcond

    def imm(self, v):
        return imm(v)

    def emit_guard_call_assembler(self, op, guard_op, arglocs, regalloc,
                                  fcond):
        if len(arglocs) == 4:
            [argloc, vloc, result_loc, tmploc] = arglocs
        else:
            [argloc, result_loc, tmploc] = arglocs
            vloc = imm(0)
        self.call_assembler(op, guard_op, argloc, vloc, result_loc, tmploc)
        self._emit_guard_may_force(guard_op,
                        regalloc._prepare_guard(guard_op))
        return fcond

    def _call_assembler_emit_call(self, addr, argloc, resloc):
        self.simple_call(addr, [argloc], result_loc=resloc)

    def _call_assembler_emit_helper_call(self, addr, arglocs, resloc):
        self.simple_call(addr, arglocs, result_loc=resloc)

    def _call_assembler_check_descr(self, value, tmploc):
        ofs = self.cpu.get_ofs_of_frame_field('jf_descr')
        self.mc.LDR_ri(r.ip.value, tmploc.value, imm=ofs)
        if check_imm_arg(value):
            self.mc.CMP_ri(r.ip.value, imm=value)
        else:
            self.mc.gen_load_int(r.lr.value, value)
            self.mc.CMP_rr(r.ip.value, r.lr.value)
        pos = self.mc.currpos()
        self.mc.BKPT()
        return pos

    def _call_assembler_patch_je(self, result_loc, jmp_location):
        pos = self.mc.currpos()
        self.mc.BKPT()
        #
        pmc = OverwritingBuilder(self.mc, jmp_location, WORD)
        pmc.B_offs(self.mc.currpos(), c.EQ)
        return pos

    def _call_assembler_load_result(self, op, result_loc):
        if op.result is not None:
            # load the return value from (tmploc, 0)
            kind = op.result.type
            descr = self.cpu.getarraydescr_for_frame(kind)
            if kind == FLOAT:
                ofs = self.cpu.unpack_arraydescr(descr)
                assert check_imm_arg(ofs)
                assert result_loc.is_vfp_reg()
                # we always have a register here, since we have to sync them
                # before call_assembler
                self.load_reg(self.mc, result_loc, r.r0, ofs=ofs)
            else:
                assert result_loc is r.r0
                ofs = self.cpu.unpack_arraydescr(descr)
                assert check_imm_arg(ofs)
                self.mc.LDR_ri(result_loc.value, result_loc.value, imm=ofs)

    def _call_assembler_patch_jmp(self, jmp_location):
        # merge point
        currpos = self.mc.currpos()
        pmc = OverwritingBuilder(self.mc, jmp_location, WORD)
        pmc.B_offs(currpos)

    # ../x86/assembler.py:668
    def redirect_call_assembler(self, oldlooptoken, newlooptoken):
        # some minimal sanity checking
        old_nbargs = oldlooptoken.compiled_loop_token._debug_nbargs
        new_nbargs = newlooptoken.compiled_loop_token._debug_nbargs
        assert old_nbargs == new_nbargs
        # we overwrite the instructions at the old _ll_function_addr
        # to start with a JMP to the new _ll_function_addr.
        # Ideally we should rather patch all existing CALLs, but well.
        oldadr = oldlooptoken._ll_function_addr
        target = newlooptoken._ll_function_addr
        # copy frame-info data
        baseofs = self.cpu.get_baseofs_of_frame_field()
        newlooptoken.compiled_loop_token.update_frame_info(
            oldlooptoken.compiled_loop_token, baseofs)
        mc = InstrBuilder(self.cpu.cpuinfo.arch_version)
        mc.B(target)
        mc.copy_to_raw_memory(oldadr)

    def emit_guard_call_may_force(self, op, guard_op, arglocs, regalloc,
                                                                    fcond):
        self._store_force_index(guard_op)
        numargs = op.numargs()
        callargs = arglocs[:numargs + 3]  # extract the arguments to the call
        guardargs = arglocs[len(callargs):]
        #
        self._emit_call(op, callargs, fcond=fcond)
        self._emit_guard_may_force(guard_op, guardargs)
        return fcond

    def _emit_guard_may_force(self, guard_op, arglocs):
        ofs = self.cpu.get_ofs_of_frame_field('jf_descr')
        self.mc.LDR_ri(r.ip.value, r.fp.value, imm=ofs)
        self.mc.CMP_ri(r.ip.value, 0)
        self._emit_guard(guard_op, arglocs, c.EQ,
                                   save_exc=True, is_guard_not_forced=True)

    def emit_guard_call_release_gil(self, op, guard_op, arglocs, regalloc,
                                                                    fcond):
        numargs = op.numargs()
        callargs = arglocs[:numargs + 3]     # extract the arguments to the call
        guardargs = arglocs[len(callargs):]  # extrat the arguments for the guard
        self._store_force_index(guard_op)
        self._emit_call(op, callargs, is_call_release_gil=True)
        self._emit_guard_may_force(guard_op, guardargs)
        return fcond

    def _store_force_index(self, guard_op):
        faildescr = guard_op.getdescr()
        ofs = self.cpu.get_ofs_of_frame_field('jf_force_descr')
        value = rffi.cast(lltype.Signed, cast_instance_to_gcref(faildescr))
        self.mc.gen_load_int(r.ip.value, value)
        self.store_reg(self.mc, r.ip, r.fp, ofs)

    def emit_op_call_malloc_gc(self, op, arglocs, regalloc, fcond):
        self.emit_op_call(op, arglocs, regalloc, fcond)
        self.propagate_memoryerror_if_r0_is_null()
        self._alignment_check()
        return fcond

    def _alignment_check(self):
        if not self.debug:
            return
        self.mc.MOV_rr(r.ip.value, r.r0.value)
        self.mc.AND_ri(r.ip.value, r.ip.value, 3)
        self.mc.CMP_ri(r.ip.value, 0)
        self.mc.MOV_rr(r.pc.value, r.pc.value, cond=c.EQ)
        self.mc.BKPT()
        self.mc.NOP()

    emit_op_float_add = gen_emit_float_op('float_add', 'VADD')
    emit_op_float_sub = gen_emit_float_op('float_sub', 'VSUB')
    emit_op_float_mul = gen_emit_float_op('float_mul', 'VMUL')
    emit_op_float_truediv = gen_emit_float_op('float_truediv', 'VDIV')

    emit_op_float_neg = gen_emit_unary_float_op('float_neg', 'VNEG')
    emit_op_float_abs = gen_emit_unary_float_op('float_abs', 'VABS')
    emit_op_math_sqrt = gen_emit_unary_float_op('math_sqrt', 'VSQRT')

    emit_op_float_lt = gen_emit_float_cmp_op('float_lt', c.VFP_LT)
    emit_op_float_le = gen_emit_float_cmp_op('float_le', c.VFP_LE)
    emit_op_float_eq = gen_emit_float_cmp_op('float_eq', c.EQ)
    emit_op_float_ne = gen_emit_float_cmp_op('float_ne', c.NE)
    emit_op_float_gt = gen_emit_float_cmp_op('float_gt', c.GT)
    emit_op_float_ge = gen_emit_float_cmp_op('float_ge', c.GE)

    emit_guard_float_lt = gen_emit_float_cmp_op_guard('float_lt', c.VFP_LT)
    emit_guard_float_le = gen_emit_float_cmp_op_guard('float_le', c.VFP_LE)
    emit_guard_float_eq = gen_emit_float_cmp_op_guard('float_eq', c.EQ)
    emit_guard_float_ne = gen_emit_float_cmp_op_guard('float_ne', c.NE)
    emit_guard_float_gt = gen_emit_float_cmp_op_guard('float_gt', c.GT)
    emit_guard_float_ge = gen_emit_float_cmp_op_guard('float_ge', c.GE)

    def emit_op_cast_float_to_int(self, op, arglocs, regalloc, fcond):
        arg, res = arglocs
        assert arg.is_vfp_reg()
        assert res.is_core_reg()
        self.mc.VCVT_float_to_int(r.svfp_ip.value, arg.value)
        self.mc.VMOV_sc(res.value, r.svfp_ip.value)
        return fcond

    def emit_op_cast_int_to_float(self, op, arglocs, regalloc, fcond):
        arg, res = arglocs
        assert res.is_vfp_reg()
        assert arg.is_core_reg()
        self.mc.VMOV_cs(r.svfp_ip.value, arg.value)
        self.mc.VCVT_int_to_float(res.value, r.svfp_ip.value)
        return fcond

    emit_op_llong_add = gen_emit_float_op('llong_add', 'VADD_i64')
    emit_op_llong_sub = gen_emit_float_op('llong_sub', 'VSUB_i64')
    emit_op_llong_and = gen_emit_float_op('llong_and', 'VAND_i64')
    emit_op_llong_or = gen_emit_float_op('llong_or', 'VORR_i64')
    emit_op_llong_xor = gen_emit_float_op('llong_xor', 'VEOR_i64')

    def emit_op_llong_to_int(self, op, arglocs, regalloc, fcond):
        loc = arglocs[0]
        res = arglocs[1]
        assert loc.is_vfp_reg()
        assert res.is_core_reg()
        self.mc.VMOV_rc(res.value, r.ip.value, loc.value)
        return fcond

    emit_op_convert_float_bytes_to_longlong = gen_emit_unary_float_op(
                                    'float_bytes_to_longlong', 'VMOV_cc')
    emit_op_convert_longlong_bytes_to_float = gen_emit_unary_float_op(
                                    'longlong_bytes_to_float', 'VMOV_cc')

    def emit_op_read_timestamp(self, op, arglocs, regalloc, fcond):
        assert 0, 'not supported'
        tmp = arglocs[0]
        res = arglocs[1]
        self.mc.MRC(15, 0, tmp.value, 15, 12, 1)
        self.mc.MOV_ri(r.ip.value, 0)
        self.mc.VMOV_cr(res.value, tmp.value, r.ip.value)
        return fcond

    def emit_op_cast_float_to_singlefloat(self, op, arglocs, regalloc, fcond):
        arg, res = arglocs
        assert arg.is_vfp_reg()
        assert res.is_core_reg()
        self.mc.VCVT_f64_f32(r.svfp_ip.value, arg.value)
        self.mc.VMOV_sc(res.value, r.svfp_ip.value)
        return fcond

    def emit_op_cast_singlefloat_to_float(self, op, arglocs, regalloc, fcond):
        arg, res = arglocs
        assert res.is_vfp_reg()
        assert arg.is_core_reg()
        self.mc.VMOV_cs(r.svfp_ip.value, arg.value)
        self.mc.VCVT_f32_f64(res.value, r.svfp_ip.value)
        return fcond

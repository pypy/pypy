from rpython.jit.backend.zarch.helper.assembler import (gen_emit_cmp_op,
        gen_emit_rr_or_rpool, gen_emit_shift, gen_emit_pool_or_rr_evenodd,
        gen_emit_imm_pool_rr)
from rpython.jit.backend.zarch.codebuilder import ZARCHGuardToken
import rpython.jit.backend.zarch.conditions as c
import rpython.jit.backend.zarch.registers as r
import rpython.jit.backend.zarch.locations as l
from rpython.jit.backend.zarch import callbuilder
from rpython.jit.backend.llsupport.descr import CallDescr
from rpython.jit.backend.llsupport.gcmap import allocate_gcmap
from rpython.jit.codewriter.effectinfo import EffectInfo

class IntOpAssembler(object):
    _mixin_ = True

    emit_int_add = gen_emit_imm_pool_rr('AGFI','AG','AGR')
    emit_int_add_ovf = emit_int_add

    def emit_int_sub(self, op, arglocs, regalloc):
        l0, l1 = arglocs
        if l1.is_imm() and not l1.is_in_pool():
            assert 0, "logical imm must reside in pool!"
        if l1.is_in_pool():
            self.mc.SG(l0, l1)
        else:
            self.mc.SGR(l0, l1)

    emit_int_sub_ovf = emit_int_sub

    emit_int_mul = gen_emit_imm_pool_rr('MSGFI', 'MSG', 'MSGR')
    def emit_int_mul_ovf(self, op, arglocs, regalloc):
        lr, lq, l1 = arglocs
        if l1.is_in_pool():
            self.mc.LG(r.SCRATCH, l1)
            l1 = r.SCRATCH
        elif l1.is_imm():
            self.mc.LGFI(r.SCRATCH, l1)
            l1 = r.SCRATCH

        mc = self.mc
        bc_one_decision = mc.CLGRJ_byte_count +\
                          mc.CLGIJ_byte_count + \
                          mc.LCGR_byte_count + \
                          mc.BRC_byte_count + \
                          mc.SPM_byte_count
        bc_one_signed = mc.LPGR_byte_count * 2 + \
                        mc.MLGR_byte_count + \
                        mc.LG_byte_count + \
                        bc_one_decision
        bc_none_signed = mc.LPGR_byte_count * 2 + \
                         mc.MLGR_byte_count + \
                         mc.LG_byte_count + \
                         mc.CLGRJ_byte_count + \
                         mc.CLGIJ_byte_count + \
                         mc.BRC_byte_count
        bc_set_overflow = mc.OIHL_byte_count + mc.SPM_byte_count

        # check left neg
        mc.CGIJ(lq, l.imm(0), c.LT, l.imm(mc.CGIJ_byte_count*2))
        mc.CGIJ(l1, l.imm(0), c.GE, l.imm(mc.CGIJ_byte_count*2 + bc_one_signed))
        mc.CGIJ(l1, l.imm(0), c.LT, l.imm(mc.CGIJ_byte_count + bc_one_signed)) # jump if both are negative
        # left or right is negative
        mc.LPGR(lq, lq)
        mc.LPGR(l1, l1)
        mc.MLGR(lr, l1)
        mc.LG(r.SCRATCH, l.pool(self.pool.constant_max_64_positive))
        # is the value greater than 2**63 ? then an overflow occured
        mc.CLGRJ(lq, r.SCRATCH, c.GT, l.imm(bc_one_decision + bc_none_signed)) # jump to over overflow
        mc.CLGIJ(lr, l.imm(0), c.GT, l.imm(bc_one_decision - mc.CLGRJ_byte_count + bc_none_signed)) # jump to overflow
        mc.LCGR(lq, lq)
        mc.SPM(r.SCRATCH) # 0x80 ... 00 clears the condition code and program mask
        mc.BRC(c.ANY, l.imm(mc.BRC_byte_count + bc_set_overflow + bc_none_signed)) # no overflow happened

        # both are positive
        mc.LPGR(lq, lq)
        mc.LPGR(l1, l1)
        mc.MLGR(lr, l1)
        off = mc.CLGRJ_byte_count + mc.CLGIJ_byte_count + \
              mc.BRC_byte_count
        mc.LG(r.SCRATCH, l.pool(self.pool.constant_64_ones))
        mc.CLGRJ(lq, r.SCRATCH, c.GT, l.imm(off)) # jump to over overflow
        mc.CLGIJ(lr, l.imm(0), c.GT, l.imm(off - mc.CLGRJ_byte_count)) # jump to overflow
        mc.BRC(c.ANY, l.imm(mc.BRC_byte_count + bc_set_overflow)) # no overflow happened

        # set overflow!
        #mc.IPM(r.SCRATCH)
        # set bit 34 & 35 -> indicates overflow
        mc.OILH(r.SCRATCH, l.imm(0x3000)) # sets OF
        mc.SPM(r.SCRATCH)

        # no overflow happended

    emit_int_floordiv = gen_emit_pool_or_rr_evenodd('DSG','DSGR')
    emit_uint_floordiv = gen_emit_pool_or_rr_evenodd('DLG','DLGR')
    # NOTE division sets one register with the modulo value, thus
    # the regalloc ensures the right register survives.
    emit_int_mod = gen_emit_pool_or_rr_evenodd('DSG','DSGR')

    def emit_int_invert(self, op, arglocs, regalloc):
        l0, = arglocs
        assert not l0.is_imm()
        self.mc.XG(l0, l.pool(self.pool.constant_64_ones))

    def emit_int_neg(self, op, arglocs, regalloc):
        l0, = arglocs
        self.mc.LCGR(l0, l0)

    def emit_int_signext(self, op, arglocs, regalloc):
        l0, = arglocs
        extend_from = op.getarg(1).getint()
        if extend_from == 1:
            self.mc.LGBR(l0, l0)
        elif extend_from == 2:
            self.mc.LGHR(l0, l0)
        elif extend_from == 4:
            self.mc.LGFR(l0, l0)
        else:
            raise AssertionError(extend_from)

    def emit_int_force_ge_zero(self, op, arglocs, resloc):
        l0, = arglocs
        off = self.mc.CGIJ_byte_count + self.mc.LGHI_byte_count
        self.mc.CGIJ(l0, l.imm(0), c.GE, l.imm(off))
        self.mc.LGHI(l0, l.imm(0))

    def emit_int_is_zero(self, op, arglocs, regalloc):
        l0, res = arglocs
        self.mc.CGHI(l0, l.imm(0))
        self.flush_cc(c.EQ, res)

    def emit_int_is_true(self, op, arglocs, regalloc):
        l0, res = arglocs
        self.mc.CGHI(l0, l.imm(0))
        self.flush_cc(c.NE, res)

    emit_int_and = gen_emit_rr_or_rpool("NGR", "NG")
    emit_int_or  = gen_emit_rr_or_rpool("OGR", "OG")
    emit_int_xor = gen_emit_rr_or_rpool("XGR", "XG")

    emit_int_rshift  = gen_emit_shift("SRAG")
    emit_int_lshift  = gen_emit_shift("SLAG")
    emit_uint_rshift = gen_emit_shift("SRLG")

    emit_int_le = gen_emit_cmp_op(c.LE)
    emit_int_lt = gen_emit_cmp_op(c.LT)
    emit_int_gt = gen_emit_cmp_op(c.GT)
    emit_int_ge = gen_emit_cmp_op(c.GE)
    emit_int_eq = gen_emit_cmp_op(c.EQ)
    emit_int_ne = gen_emit_cmp_op(c.NE)

    emit_ptr_eq = emit_int_eq
    emit_ptr_ne = emit_int_ne

    emit_instance_ptr_eq = emit_ptr_eq
    emit_instance_ptr_ne = emit_ptr_ne

    emit_uint_le = gen_emit_cmp_op(c.LE, signed=False)
    emit_uint_lt = gen_emit_cmp_op(c.LT, signed=False)
    emit_uint_gt = gen_emit_cmp_op(c.GT, signed=False)
    emit_uint_ge = gen_emit_cmp_op(c.GE, signed=False)

class FloatOpAssembler(object):
    _mixin_ = True

    emit_float_add = gen_emit_rr_or_rpool('ADBR','ADB')
    emit_float_sub = gen_emit_rr_or_rpool('SDBR','SDB')
    emit_float_mul = gen_emit_rr_or_rpool('MDBR','MDB')
    emit_float_truediv = gen_emit_rr_or_rpool('DDBR','DDB')

    emit_float_lt = gen_emit_cmp_op(c.LT, fp=True)
    emit_float_le = gen_emit_cmp_op(c.LE, fp=True)
    emit_float_eq = gen_emit_cmp_op(c.EQ, fp=True)
    emit_float_ne = gen_emit_cmp_op(c.NE, fp=True)
    emit_float_gt = gen_emit_cmp_op(c.GT, fp=True)
    emit_float_ge = gen_emit_cmp_op(c.GE, fp=True)

    def emit_float_neg(self, op, arglocs, regalloc):
        l0, = arglocs
        self.mc.LCDBR(l0, l0)

    def emit_float_abs(self, op, arglocs, regalloc):
        l0, = arglocs
        self.mc.LPDBR(l0, l0)

    def emit_cast_float_to_int(self, op, arglocs, regalloc):
        f0, r0 = arglocs
        self.mc.CGDBR(r0, c.FP_TOWARDS_ZERO, f0)

    def emit_cast_int_to_float(self, op, arglocs, regalloc):
        r0, f0 = arglocs
        self.mc.CDGBR(f0, r0)

class CallOpAssembler(object):

    _mixin_ = True

    def _emit_call(self, op, arglocs, is_call_release_gil=False):
        resloc = arglocs[0]
        func_index = 1 + is_call_release_gil
        adr = arglocs[func_index]
        arglist = arglocs[func_index+1:]

        cb = callbuilder.CallBuilder(self, adr, arglist, resloc)

        descr = op.getdescr()
        assert isinstance(descr, CallDescr)
        cb.argtypes = descr.get_arg_types()
        cb.restype  = descr.get_result_type()

        if is_call_release_gil:
            saveerrloc = arglocs[1]
            assert saveerrloc.is_imm()
            cb.emit_call_release_gil(saveerrloc.value)
        else:
            cb.emit()

    def _genop_call(self, op, arglocs, regalloc):
        oopspecindex = regalloc.get_oopspecindex(op)
        if oopspecindex == EffectInfo.OS_MATH_SQRT:
            return self._emit_math_sqrt(op, arglocs, regalloc)
        if oopspecindex == EffectInfo.OS_THREADLOCALREF_GET:
            return self._emit_threadlocalref_get(op, arglocs, regalloc)
        self._emit_call(op, arglocs)

    emit_call_i = _genop_call
    emit_call_r = _genop_call
    emit_call_f = _genop_call
    emit_call_n = _genop_call

    def _genop_call_may_force(self, op, arglocs, regalloc):
        self._store_force_index(self._find_nearby_operation(regalloc, +1))
        self._emit_call(op, arglocs)

    emit_call_may_force_i = _genop_call_may_force
    emit_call_may_force_r = _genop_call_may_force
    emit_call_may_force_f = _genop_call_may_force
    emit_call_may_force_n = _genop_call_may_force

    def _genop_call_release_gil(self, op, arglocs, regalloc):
        self._store_force_index(self._find_nearby_operation(regalloc, +1))
        self._emit_call(op, arglocs, is_call_release_gil=True)

    emit_call_release_gil_i = _genop_call_release_gil
    emit_call_release_gil_f = _genop_call_release_gil
    emit_call_release_gil_n = _genop_call_release_gil

    def _store_force_index(self, guard_op):
        assert (guard_op.getopnum() == rop.GUARD_NOT_FORCED or
                guard_op.getopnum() == rop.GUARD_NOT_FORCED_2)
        faildescr = guard_op.getdescr()
        ofs = self.cpu.get_ofs_of_frame_field('jf_force_descr')
        self.mc.load_imm(r.SCRATCH, rffi.cast(lltype.Signed,
                                           cast_instance_to_gcref(faildescr)))
        self.mc.store(r.SCRATCH.value, r.SPP.value, ofs)

    def _find_nearby_operation(self, regalloc, delta):
        return regalloc.operations[regalloc.rm.position + delta]

    _COND_CALL_SAVE_REGS = [r.r3, r.r4, r.r5, r.r6, r.r12]

    def emit_cond_call(self, op, arglocs, regalloc):
        fcond = self.guard_success_cc
        self.guard_success_cc = c.cond_none
        assert fcond != c.cond_none
        fcond = c.negate(fcond)

        jmp_adr = self.mc.get_relative_pos()
        self.mc.trap()        # patched later to a 'bc'

        self.load_gcmap(self.mc, r.r2, regalloc.get_gcmap())

        # save away r3, r4, r5, r6, r12 into the jitframe
        should_be_saved = [
            reg for reg in self._regalloc.rm.reg_bindings.itervalues()
                if reg in self._COND_CALL_SAVE_REGS]
        self._push_core_regs_to_jitframe(self.mc, should_be_saved)
        #
        # load the 0-to-4 arguments into these registers, with the address of
        # the function to call into r12
        remap_frame_layout(self, arglocs,
                           [r.r12, r.r3, r.r4, r.r5, r.r6][:len(arglocs)],
                           r.SCRATCH)
        #
        # figure out which variant of cond_call_slowpath to call, and call it
        callee_only = False
        floats = False
        for reg in regalloc.rm.reg_bindings.values():
            if reg not in regalloc.rm.save_around_call_regs:
                break
        else:
            callee_only = True
        if regalloc.fprm.reg_bindings:
            floats = True
        cond_call_adr = self.cond_call_slowpath[floats * 2 + callee_only]
        self.mc.bl_abs(cond_call_adr)
        # restoring the registers saved above, and doing pop_gcmap(), is left
        # to the cond_call_slowpath helper.  We never have any result value.
        relative_target = self.mc.currpos() - jmp_adr
        pmc = OverwritingBuilder(self.mc, jmp_adr, 1)
        BI, BO = c.encoding[fcond]
        pmc.bc(BO, BI, relative_target)
        pmc.overwrite()
        # might be overridden again to skip over the following
        # guard_no_exception too
        self.previous_cond_call_jcond = jmp_adr, BI, BO

class GuardOpAssembler(object):
    _mixin_ = True

    def _emit_guard(self, op, arglocs, is_guard_not_invalidated=False):
        if is_guard_not_invalidated:
            fcond = c.cond_none
        else:
            fcond = self.guard_success_cc
            self.guard_success_cc = c.cond_none
            assert fcond != c.cond_none
            fcond = c.negate(fcond)
        token = self.build_guard_token(op, arglocs[0].value, arglocs[1:], fcond)
        token.pos_jump_offset = self.mc.currpos()
        assert token.guard_not_invalidated() == is_guard_not_invalidated
        if not is_guard_not_invalidated:
            self.mc.reserve_guard_branch()     # has to be patched later on
        self.pending_guard_tokens.append(token)

    def build_guard_token(self, op, frame_depth, arglocs, fcond):
        descr = op.getdescr()
        gcmap = allocate_gcmap(self, frame_depth, r.JITFRAME_FIXED_SIZE)
        token = ZARCHGuardToken(self.cpu, gcmap, descr, op.getfailargs(),
                              arglocs, op.getopnum(), frame_depth,
                              fcond)
        return token

    def emit_guard_true(self, op, arglocs, regalloc):
        self._emit_guard(op, arglocs)

    def emit_guard_false(self, op, arglocs, regalloc):
        self.guard_success_cc = c.negate(self.guard_success_cc)
        self._emit_guard(op, arglocs)

    def emit_guard_overflow(self, op, arglocs, regalloc):
        self.guard_success_cc = c.OF
        self._emit_guard(op, arglocs)

    def emit_guard_no_overflow(self, op, arglocs, regalloc):
        self.guard_success_cc = c.NO
        self._emit_guard(op, arglocs)

    def emit_guard_value(self, op, arglocs, regalloc):
        l0 = arglocs[0]
        l1 = arglocs[1]
        failargs = arglocs[2:]

        if l0.is_reg():
            if l1.is_imm():
                self.mc.cmp_op(l0, l1, imm=True)
            else:
                self.mc.cmp_op(l0, l1)
        elif l0.is_fp_reg():
            assert l1.is_fp_reg()
            self.mc.cmp_op(l0, l1, fp=True)
        self.guard_success_cc = c.EQ
        self._emit_guard(op, failargs)

    emit_guard_nonnull = emit_guard_true
    emit_guard_isnull = emit_guard_false

    def emit_guard_class(self, op, arglocs, regalloc):
        self._cmp_guard_class(op, arglocs, regalloc)
        self.guard_success_cc = c.EQ
        self._emit_guard(op, arglocs[2:])

    def emit_guard_nonnull_class(self, op, arglocs, regalloc):
        self.mc.cmp_op(0, arglocs[0].value, 1, imm=True, signed=False)
        patch_pos = self.mc.currpos()
        self.mc.trap()
        self._cmp_guard_class(op, arglocs, regalloc)
        pmc = OverwritingBuilder(self.mc, patch_pos, 1)
        pmc.blt(self.mc.currpos() - patch_pos)
        pmc.overwrite()
        self.guard_success_cc = c.EQ
        self._emit_guard(op, arglocs[2:])

    def _cmp_guard_class(self, op, locs, regalloc):
        offset = self.cpu.vtable_offset
        if offset is not None:
            # could be one instruction shorter, but don't care because
            # it's not this case that is commonly translated
            self.mc.load(r.SCRATCH.value, locs[0].value, offset)
            self.mc.load_imm(r.SCRATCH2, locs[1].value)
            self.mc.cmp_op(0, r.SCRATCH.value, r.SCRATCH2.value)
        else:
            expected_typeid = (self.cpu.gc_ll_descr
                    .get_typeid_from_classptr_if_gcremovetypeptr(locs[1].value))
            self._cmp_guard_gc_type(locs[0], expected_typeid)

    def _read_typeid(self, targetreg, loc_ptr):
        # Note that the typeid half-word is at offset 0 on a little-endian
        # machine; it is at offset 2 or 4 on a big-endian machine.
        assert self.cpu.supports_guard_gc_type
        if IS_PPC_32:
            self.mc.lhz(targetreg.value, loc_ptr.value, 2 * IS_BIG_ENDIAN)
        else:
            self.mc.lwz(targetreg.value, loc_ptr.value, 4 * IS_BIG_ENDIAN)

    def _cmp_guard_gc_type(self, loc_ptr, expected_typeid):
        self._read_typeid(r.SCRATCH2, loc_ptr)
        assert 0 <= expected_typeid <= 0x7fffffff   # 4 bytes are always enough
        if expected_typeid > 0xffff:     # if 2 bytes are not enough
            self.mc.subis(r.SCRATCH2.value, r.SCRATCH2.value,
                          expected_typeid >> 16)
            expected_typeid = expected_typeid & 0xffff
        self.mc.cmp_op(0, r.SCRATCH2.value, expected_typeid,
                       imm=True, signed=False)

    def emit_guard_gc_type(self, op, arglocs, regalloc):
        self._cmp_guard_gc_type(arglocs[0], arglocs[1].value)
        self.guard_success_cc = c.EQ
        self._emit_guard(op, arglocs[2:])

    def emit_guard_is_object(self, op, arglocs, regalloc):
        assert self.cpu.supports_guard_gc_type
        loc_object = arglocs[0]
        # idea: read the typeid, fetch one byte of the field 'infobits' from
        # the big typeinfo table, and check the flag 'T_IS_RPYTHON_INSTANCE'.
        base_type_info, shift_by, sizeof_ti = (
            self.cpu.gc_ll_descr.get_translated_info_for_typeinfo())
        infobits_offset, IS_OBJECT_FLAG = (
            self.cpu.gc_ll_descr.get_translated_info_for_guard_is_object())

        self._read_typeid(r.SCRATCH2, loc_object)
        self.mc.load_imm(r.SCRATCH, base_type_info + infobits_offset)
        assert shift_by == 0     # on PPC64; fixme for PPC32
        self.mc.lbzx(r.SCRATCH2.value, r.SCRATCH2.value, r.SCRATCH.value)
        self.mc.andix(r.SCRATCH2.value, r.SCRATCH2.value, IS_OBJECT_FLAG & 0xff)
        self.guard_success_cc = c.NE
        self._emit_guard(op, arglocs[1:])

    def emit_guard_subclass(self, op, arglocs, regalloc):
        assert self.cpu.supports_guard_gc_type
        loc_object = arglocs[0]
        loc_check_against_class = arglocs[1]
        offset = self.cpu.vtable_offset
        offset2 = self.cpu.subclassrange_min_offset
        if offset is not None:
            # read this field to get the vtable pointer
            self.mc.load(r.SCRATCH2.value, loc_object.value, offset)
            # read the vtable's subclassrange_min field
            assert _check_imm_arg(offset2)
            self.mc.ld(r.SCRATCH2.value, r.SCRATCH2.value, offset2)
        else:
            # read the typeid
            self._read_typeid(r.SCRATCH, loc_object)
            # read the vtable's subclassrange_min field, as a single
            # step with the correct offset
            base_type_info, shift_by, sizeof_ti = (
                self.cpu.gc_ll_descr.get_translated_info_for_typeinfo())
            self.mc.load_imm(r.SCRATCH2, base_type_info + sizeof_ti + offset2)
            assert shift_by == 0     # on PPC64; fixme for PPC32
            self.mc.ldx(r.SCRATCH2.value, r.SCRATCH2.value, r.SCRATCH.value)
        # get the two bounds to check against
        vtable_ptr = loc_check_against_class.getint()
        vtable_ptr = rffi.cast(rclass.CLASSTYPE, vtable_ptr)
        check_min = vtable_ptr.subclassrange_min
        check_max = vtable_ptr.subclassrange_max
        assert check_max > check_min
        check_diff = check_max - check_min - 1
        # right now, a full PyPy uses less than 6000 numbers,
        # so we'll assert here that it always fit inside 15 bits
        assert 0 <= check_min <= 0x7fff
        assert 0 <= check_diff <= 0xffff
        # check by doing the unsigned comparison (tmp - min) < (max - min)
        self.mc.subi(r.SCRATCH2.value, r.SCRATCH2.value, check_min)
        self.mc.cmp_op(0, r.SCRATCH2.value, check_diff, imm=True, signed=False)
        # the guard passes if we get a result of "below or equal"
        self.guard_success_cc = c.LE
        self._emit_guard(op, arglocs[2:])

    def emit_guard_not_invalidated(self, op, arglocs, regalloc):
        self._emit_guard(op, arglocs, is_guard_not_invalidated=True)

    def emit_guard_not_forced(self, op, arglocs, regalloc):
        ofs = self.cpu.get_ofs_of_frame_field('jf_descr')
        self.mc.ld(r.SCRATCH.value, r.SPP.value, ofs)
        self.mc.cmp_op(0, r.SCRATCH.value, 0, imm=True)
        self.guard_success_cc = c.EQ
        self._emit_guard(op, arglocs)

    def emit_guard_not_forced_2(self, op, arglocs, regalloc):
        guard_token = self.build_guard_token(op, arglocs[0].value, arglocs[1:],
                                             c.cond_none)
        self._finish_gcmap = guard_token.gcmap
        self._store_force_index(op)
        self.store_info_on_descr(0, guard_token)

class MiscOpAssembler(object):
    _mixin_ = True

    def _genop_same_as(self, op, arglocs, regalloc):
        argloc, resloc = arglocs
        if argloc is not resloc:
            self.regalloc_mov(argloc, resloc)

    emit_same_as_i = _genop_same_as
    emit_same_as_r = _genop_same_as
    emit_same_as_f = _genop_same_as
    emit_cast_ptr_to_int = _genop_same_as
    emit_cast_int_to_ptr = _genop_same_as

    def emit_increment_debug_counter(self, op, arglocs, regalloc):
        addr, scratch = arglocs
        self.mc.LG(scratch, l.addr(0,addr))
        self.mc.AGHI(scratch, l.imm(1))
        self.mc.STG(scratch, l.addr(0,addr))

    def emit_debug_merge_point(self, op, arglocs, regalloc):
        pass

    emit_jit_debug = emit_debug_merge_point
    emit_keepalive = emit_debug_merge_point

    def emit_enter_portal_frame(self, op, arglocs, regalloc):
        self.enter_portal_frame(op)

    def emit_leave_portal_frame(self, op, arglocs, regalloc):
        self.leave_portal_frame(op)

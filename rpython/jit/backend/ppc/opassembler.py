from rpython.jit.backend.ppc.helper.assembler import gen_emit_cmp_op
from rpython.jit.backend.ppc.helper.regalloc import _check_imm_arg
import rpython.jit.backend.ppc.condition as c
import rpython.jit.backend.ppc.register as r
from rpython.jit.backend.ppc.locations import imm
from rpython.jit.backend.ppc.locations import imm as make_imm_loc
from rpython.jit.backend.ppc.arch import (IS_PPC_32, IS_PPC_64, WORD,
                                          MAX_REG_PARAMS, MAX_FREG_PARAMS,
                                          PARAM_SAVE_AREA_OFFSET,
                                          THREADLOCAL_ADDR_OFFSET,
                                          IS_BIG_ENDIAN)

from rpython.jit.metainterp.history import (JitCellToken, TargetToken, Box,
                                            AbstractFailDescr, FLOAT, INT, REF)
from rpython.rlib.objectmodel import we_are_translated
from rpython.jit.backend.ppc.helper.assembler import (Saved_Volatiles)
from rpython.jit.backend.ppc.jump import remap_frame_layout
from rpython.jit.backend.ppc.codebuilder import (OverwritingBuilder, scratch_reg,
                                                 PPCBuilder, PPCGuardToken)
from rpython.jit.backend.ppc.regalloc import TempPtr, TempInt
from rpython.jit.backend.llsupport import symbolic
from rpython.jit.backend.llsupport.descr import InteriorFieldDescr, CallDescr
from rpython.jit.backend.llsupport.gcmap import allocate_gcmap
from rpython.rtyper.lltypesystem import rstr, rffi, lltype
from rpython.rtyper.annlowlevel import cast_instance_to_gcref
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.jit.backend.ppc import callbuilder

class IntOpAssembler(object):
        
    _mixin_ = True

    def emit_int_add(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        assert not l0.is_imm()
        if l1.is_imm():
            self.mc.addi(res.value, l0.value, l1.value)
        else:
            self.mc.add(res.value, l0.value, l1.value)

    def emit_int_sub(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        assert not l0.is_imm()
        if l1.is_imm():
            self.mc.subi(res.value, l0.value, l1.value)
        else:
            self.mc.sub(res.value, l0.value, l1.value)
 
    def emit_int_mul(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        assert not l0.is_imm()
        if l1.is_imm():
            self.mc.mulli(res.value, l0.value, l1.value)
        elif IS_PPC_32:
            self.mc.mullw(res.value, l0.value, l1.value)
        else:
            self.mc.mulld(res.value, l0.value, l1.value)

    def do_emit_int_binary_ovf(self, op, arglocs, emit):
        l0, l1, res = arglocs[0], arglocs[1], arglocs[2]
        self.mc.load_imm(r.SCRATCH, 0)
        self.mc.mtxer(r.SCRATCH.value)
        emit(res.value, l0.value, l1.value)

    def emit_int_add_ovf(self, op, arglocs, regalloc):
        self.do_emit_int_binary_ovf(op, arglocs, self.mc.addox)

    def emit_int_sub_ovf(self, op, arglocs, regalloc):
        self.do_emit_int_binary_ovf(op, arglocs, self.mc.subox)

    def emit_int_mul_ovf(self, op, arglocs, regalloc):
        if IS_PPC_32:
            self.do_emit_int_binary_ovf(op, arglocs, self.mc.mullwox)
        else:
            self.do_emit_int_binary_ovf(op, arglocs, self.mc.mulldox)

    def emit_int_floordiv(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        if IS_PPC_32:
            self.mc.divw(res.value, l0.value, l1.value)
        else:
            self.mc.divd(res.value, l0.value, l1.value)

    def emit_int_mod(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        if IS_PPC_32:
            self.mc.divw(r.r0.value, l0.value, l1.value)
            self.mc.mullw(r.r0.value, r.r0.value, l1.value)
        else:
            self.mc.divd(r.r0.value, l0.value, l1.value)
            self.mc.mulld(r.r0.value, r.r0.value, l1.value)
        self.mc.subf(r.r0.value, r.r0.value, l0.value)
        self.mc.mr(res.value, r.r0.value)

    def emit_int_and(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        self.mc.and_(res.value, l0.value, l1.value)

    def emit_int_or(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        self.mc.or_(res.value, l0.value, l1.value)

    def emit_int_xor(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        self.mc.xor(res.value, l0.value, l1.value)
        
    def emit_int_lshift(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        if IS_PPC_32:
            self.mc.slw(res.value, l0.value, l1.value)
        else:
            self.mc.sld(res.value, l0.value, l1.value)

    def emit_int_rshift(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        if IS_PPC_32:
            self.mc.sraw(res.value, l0.value, l1.value)
        else:
            self.mc.srad(res.value, l0.value, l1.value)

    def emit_uint_rshift(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        if IS_PPC_32:
            self.mc.srw(res.value, l0.value, l1.value)
        else:
            self.mc.srd(res.value, l0.value, l1.value)
    
    def emit_uint_floordiv(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        if IS_PPC_32:
            self.mc.divwu(res.value, l0.value, l1.value)
        else:
            self.mc.divdu(res.value, l0.value, l1.value)

    emit_int_le = gen_emit_cmp_op(c.LE)
    emit_int_lt = gen_emit_cmp_op(c.LT)
    emit_int_gt = gen_emit_cmp_op(c.GT)
    emit_int_ge = gen_emit_cmp_op(c.GE)
    emit_int_eq = gen_emit_cmp_op(c.EQ)
    emit_int_ne = gen_emit_cmp_op(c.NE)

    emit_uint_lt = gen_emit_cmp_op(c.LT, signed=False)
    emit_uint_le = gen_emit_cmp_op(c.LE, signed=False)
    emit_uint_gt = gen_emit_cmp_op(c.GT, signed=False)
    emit_uint_ge = gen_emit_cmp_op(c.GE, signed=False)

    emit_int_is_zero = emit_int_eq   # EQ to 0
    emit_int_is_true = emit_int_ne   # NE to 0

    emit_ptr_eq = emit_int_eq
    emit_ptr_ne = emit_int_ne

    emit_instance_ptr_eq = emit_ptr_eq
    emit_instance_ptr_ne = emit_ptr_ne

    def emit_int_neg(self, op, arglocs, regalloc):
        l0, res = arglocs
        self.mc.neg(res.value, l0.value)

    def emit_int_invert(self, op, arglocs, regalloc):
        l0, res = arglocs
        self.mc.not_(res.value, l0.value)

    def emit_int_signext(self, op, arglocs, regalloc):
        l0, res = arglocs
        extend_from = op.getarg(1).getint()
        if extend_from == 1:
            self.mc.extsb(res.value, l0.value)
        elif extend_from == 2:
            self.mc.extsh(res.value, l0.value)
        elif extend_from == 4:
            self.mc.extsw(res.value, l0.value)
        else:
            raise AssertionError(extend_from)

    def emit_int_force_ge_zero(self, op, arglocs, regalloc):
        arg, res = arglocs
        with scratch_reg(self.mc):
            self.mc.nor(r.SCRATCH.value, arg.value, arg.value)
            if IS_PPC_32:
                self.mc.srawi(r.SCRATCH.value, r.SCRATCH.value, 31)
            else:
                # sradi (scratch, scratch, 63)
                self.mc.sradi(r.SCRATCH.value, r.SCRATCH.value, 1, 31)
            self.mc.and_(res.value, arg.value, r.SCRATCH.value)

class FloatOpAssembler(object):
    _mixin_ = True

    def emit_float_add(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        self.mc.fadd(res.value, l0.value, l1.value)

    def emit_float_sub(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        self.mc.fsub(res.value, l0.value, l1.value)

    def emit_float_mul(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        self.mc.fmul(res.value, l0.value, l1.value)

    def emit_float_truediv(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        self.mc.fdiv(res.value, l0.value, l1.value)

    def emit_float_neg(self, op, arglocs, regalloc):
        l0, res = arglocs
        self.mc.fneg(res.value, l0.value)

    def emit_float_abs(self, op, arglocs, regalloc):
        l0, res = arglocs
        self.mc.fabs(res.value, l0.value)

    def _emit_math_sqrt(self, op, arglocs, regalloc):
        l0, res = arglocs
        self.mc.fsqrt(res.value, l0.value)

    emit_float_le = gen_emit_cmp_op(c.LE, fp=True)
    emit_float_lt = gen_emit_cmp_op(c.LT, fp=True)
    emit_float_gt = gen_emit_cmp_op(c.GT, fp=True)
    emit_float_ge = gen_emit_cmp_op(c.GE, fp=True)
    emit_float_eq = gen_emit_cmp_op(c.EQ, fp=True)
    emit_float_ne = gen_emit_cmp_op(c.NE, fp=True)

    def emit_cast_float_to_int(self, op, arglocs, regalloc):
        l0, temp_loc, res = arglocs
        self.mc.fctidz(temp_loc.value, l0.value)
        self.mc.stfd(temp_loc.value, r.SP.value, PARAM_SAVE_AREA_OFFSET)
        self.mc.ld(res.value, r.SP.value, PARAM_SAVE_AREA_OFFSET)

    def emit_cast_int_to_float(self, op, arglocs, regalloc):
        l0, res = arglocs
        self.mc.std(l0.value, r.SP.value, PARAM_SAVE_AREA_OFFSET)
        self.mc.lfd(res.value, r.SP.value, PARAM_SAVE_AREA_OFFSET)
        self.mc.fcfid(res.value, res.value)

    def emit_convert_float_bytes_to_longlong(self, op, arglocs, regalloc):
        l0, res = arglocs
        self.mc.stfd(l0.value, r.SP.value, PARAM_SAVE_AREA_OFFSET)
        self.mc.ld(res.value, r.SP.value, PARAM_SAVE_AREA_OFFSET)

    def emit_convert_longlong_bytes_to_float(self, op, arglocs, regalloc):
        l0, res = arglocs
        self.mc.std(l0.value, r.SP.value, PARAM_SAVE_AREA_OFFSET)
        self.mc.lfd(res.value, r.SP.value, PARAM_SAVE_AREA_OFFSET)

class GuardOpAssembler(object):

    _mixin_ = True

    def _emit_guard(self, op, arglocs, save_exc=False,
                    is_guard_not_invalidated=False,
                    is_guard_not_forced=False):
        if is_guard_not_invalidated:
            fcond = c.cond_none
        else:
            fcond = self.guard_success_cc
            self.guard_success_cc = c.cond_none
            assert fcond != c.cond_none
            fcond = c.negate(fcond)
        token = self.build_guard_token(op, arglocs[0].value, arglocs[1:],
                                       fcond, save_exc, is_guard_not_invalidated,
                                       is_guard_not_forced)
        token.pos_jump_offset = self.mc.currpos()
        if not is_guard_not_invalidated:
            self.mc.trap()     # has to be patched later on
        self.pending_guard_tokens.append(token)

    def build_guard_token(self, op, frame_depth, arglocs, fcond, save_exc,
                          is_guard_not_invalidated=False,
                          is_guard_not_forced=False):
        descr = op.getdescr()
        gcmap = allocate_gcmap(self, frame_depth, r.JITFRAME_FIXED_SIZE)
        token = PPCGuardToken(self.cpu, gcmap, descr, op.getfailargs(),
                              arglocs, save_exc, frame_depth,
                              is_guard_not_invalidated, is_guard_not_forced,
                              fcond)
        return token

    def emit_guard_true(self, op, arglocs, regalloc):
        self._emit_guard(op, arglocs)

    def emit_guard_false(self, op, arglocs, regalloc):
        self.guard_success_cc = c.negate(self.guard_success_cc)
        self._emit_guard(op, arglocs)

    def emit_guard_overflow(self, op, arglocs, regalloc):
        self.guard_success_cc = c.SO
        self._emit_guard(op, arglocs)

    def emit_guard_no_overflow(self, op, arglocs, regalloc):
        self.guard_success_cc = c.NS
        self._emit_guard(op, arglocs)

    def emit_guard_value(self, op, arglocs, regalloc):
        l0 = arglocs[0]
        l1 = arglocs[1]
        failargs = arglocs[2:]

        if l0.is_reg():
            if l1.is_imm():
                self.mc.cmp_op(0, l0.value, l1.getint(), imm=True)
            else:
                self.mc.cmp_op(0, l0.value, l1.value)
        elif l0.is_fp_reg():
            assert l1.is_fp_reg()
            self.mc.cmp_op(0, l0.value, l1.value, fp=True)
        self.guard_success_cc = c.EQ
        self._emit_guard(op, failargs)

    emit_guard_nonnull = emit_guard_true
    emit_guard_isnull = emit_guard_false

    def emit_guard_class(self, op, arglocs, regalloc):
        self._cmp_guard_class(op, arglocs, regalloc)
        self.guard_success_cc = c.EQ
        self._emit_guard(op, arglocs[3:])

    def emit_guard_nonnull_class(self, op, arglocs, regalloc):
        self.mc.cmp_op(0, arglocs[0].value, 1, imm=True, signed=False)
        patch_pos = self.mc.currpos()
        self.mc.trap()
        self._cmp_guard_class(op, arglocs, regalloc)
        pmc = OverwritingBuilder(self.mc, patch_pos, 1)
        pmc.blt(self.mc.currpos() - patch_pos)
        pmc.overwrite()
        self.guard_success_cc = c.EQ
        self._emit_guard(op, arglocs[3:])

    def _cmp_guard_class(self, op, locs, regalloc):
        offset = locs[2]
        if offset is not None:
            with scratch_reg(self.mc):
                self.mc.load(r.SCRATCH.value, locs[0].value, offset.value)
                self.mc.cmp_op(0, r.SCRATCH.value, locs[1].value)
        else:
            typeid = locs[1]
            # here, we have to go back from 'classptr' to the value expected
            # from reading the half-word in the object header.  Note that
            # this half-word is at offset 0 on a little-endian machine;
            # but it is at offset 2 (32 bit) or 4 (64 bit) on a
            # big-endian machine.
            with scratch_reg(self.mc):
                if IS_PPC_32:
                    self.mc.lhz(r.SCRATCH.value, locs[0].value, 2)
                else:
                    self.mc.lwz(r.SCRATCH.value, locs[0].value, 4)
                self.mc.cmp_op(0, r.SCRATCH.value, typeid.value, imm=typeid.is_imm())

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
                                             c.cond_none, save_exc=False)
        self._finish_gcmap = guard_token.gcmap
        self._store_force_index(op)
        self.store_info_on_descr(0, guard_token)


class MiscOpAssembler(object):

    _mixin_ = True

    def emit_label(self, op, arglocs, regalloc):
        pass

    def emit_increment_debug_counter(self, op, arglocs, regalloc):
        [addr_loc, value_loc] = arglocs
        self.mc.load(value_loc.value, addr_loc.value, 0)
        self.mc.addi(value_loc.value, value_loc.value, 1)   # can't use r0!
        self.mc.store(value_loc.value, addr_loc.value, 0)

    def emit_finish(self, op, arglocs, regalloc):
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        if len(arglocs) > 1:
            [return_val, fail_descr_loc] = arglocs
            if op.getarg(0).type == FLOAT:
                self.mc.stfd(return_val.value, r.SPP.value, base_ofs)
            else:
                self.mc.std(return_val.value, r.SPP.value, base_ofs)
        else:
            [fail_descr_loc] = arglocs

        ofs = self.cpu.get_ofs_of_frame_field('jf_descr')
        self.mc.load_imm(r.r5, fail_descr_loc.getint())
        self.mc.std(r.r5.value, r.SPP.value, ofs)

        ## XXX: gcmap logic here:
        ## arglist = op.getarglist()
        ## if arglist and arglist[0].type == REF:
        ##     if self._finish_gcmap:
        ##         # we're returning with a guard_not_forced_2, and
        ##         # additionally we need to say that eax/rax contains
        ##         # a reference too:
        ##         self._finish_gcmap[0] |= r_uint(1)
        ##         gcmap = self._finish_gcmap
        ##     else:
        ##         gcmap = self.gcmap_for_finish
        ##     self.push_gcmap(self.mc, gcmap, store=True)
        ## elif self._finish_gcmap:
        ##     # we're returning with a guard_not_forced_2
        ##     gcmap = self._finish_gcmap
        ##     self.push_gcmap(self.mc, gcmap, store=True)
        ## else:
        ##     # note that the 0 here is redundant, but I would rather
        ##     # keep that one and kill all the others
        ##     ofs = self.cpu.get_ofs_of_frame_field('jf_gcmap')
        ##     self.mc.MOV_bi(ofs, 0)
        # exit function
        self._call_footer()

    def emit_jump(self, op, arglocs, regalloc):
        # The backend's logic assumes that the target code is in a piece of
        # assembler that was also called with the same number of arguments,
        # so that the locations [ebp+8..] of the input arguments are valid
        # stack locations both before and after the jump.
        #
        descr = op.getdescr()
        assert isinstance(descr, TargetToken)
        my_nbargs = self.current_clt._debug_nbargs
        target_nbargs = descr._ppc_clt._debug_nbargs
        assert my_nbargs == target_nbargs

        if descr in self.target_tokens_currently_compiling:
            self.mc.b_offset(descr._ppc_loop_code)
        else:
            self.mc.b_abs(descr._ppc_loop_code)

    def emit_same_as(self, op, arglocs, regalloc):
        argloc, resloc = arglocs
        if argloc is not resloc:
            self.regalloc_mov(argloc, resloc)

    emit_cast_ptr_to_int = emit_same_as
    emit_cast_int_to_ptr = emit_same_as

    def emit_guard_no_exception(self, op, arglocs, regalloc):
        self.mc.load_from_addr(r.SCRATCH2, self.cpu.pos_exception())
        self.mc.cmp_op(0, r.SCRATCH2.value, 0, imm=True)
        self.guard_success_cc = c.EQ
        self._emit_guard(op, arglocs, save_exc=True)
        # If the previous operation was a COND_CALL, overwrite its conditional
        # jump to jump over this GUARD_NO_EXCEPTION as well, if we can
        if self._find_nearby_operation(regalloc,-1).getopnum() == rop.COND_CALL:
            jmp_adr, BI, BO = self.previous_cond_call_jcond
            relative_target = self.mc.currpos() - jmp_adr
            pmc = OverwritingBuilder(self.mc, jmp_adr, 1)
            pmc.bc(BO, BI, relative_target)
            pmc.overwrite()

    def emit_guard_exception(self, op, arglocs, regalloc):
        # XXX FIXME
        # XXX pos_exc_value and pos_exception are 8 bytes apart, don't need both
        loc, loc1, resloc, pos_exc_value, pos_exception = arglocs[:5]
        failargs = arglocs[5:]
        self.mc.load_imm(loc1, pos_exception.value)
        self.mc.load(r.SCRATCH.value, loc1.value, 0)
        self.mc.cmp_op(0, r.SCRATCH.value, loc.value)
        self.guard_success_cc = c.EQ
        self._emit_guard(op, failargs, save_exc=True)
        self.mc.load_imm(loc, pos_exc_value.value)

        if resloc:
            self.mc.load(resloc.value, loc.value, 0)

        self.mc.load_imm(r.SCRATCH, 0)
        self.mc.store(r.SCRATCH.value, loc.value, 0)
        self.mc.store(r.SCRATCH.value, loc1.value, 0)


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

    def emit_call(self, op, arglocs, regalloc):
        oopspecindex = regalloc.get_oopspecindex(op)
        if oopspecindex == EffectInfo.OS_MATH_SQRT:
            return self._emit_math_sqrt(op, arglocs, regalloc)
        self._emit_call(op, arglocs)

    def emit_call_may_force(self, op, arglocs, regalloc):
        self._store_force_index(self._find_nearby_operation(regalloc, +1))
        self._emit_call(op, arglocs)

    def emit_call_release_gil(self, op, arglocs, regalloc):
        self._store_force_index(self._find_nearby_operation(regalloc, +1))
        self._emit_call(op, arglocs, is_call_release_gil=True)

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

    def emit_cond_call(self, op, arglocs, regalloc):
        fcond = self.guard_success_cc
        self.guard_success_cc = c.cond_none
        assert fcond != c.cond_none
        fcond = c.negate(fcond)

        jmp_adr = self.mc.get_relative_pos()
        self.mc.trap()        # patched later to a 'bc'

        # XXX load_gcmap XXX -> r2

        # save away r3, r4, r5, r6, r12 into the jitframe
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        should_be_saved = self._regalloc.rm.reg_bindings.values()
        for gpr in [r.r3, r.r4, r.r5, r.r6, r.r12]:
            if gpr not in should_be_saved:
                continue
            v = self.cpu.all_reg_indexes[gpr.value]
            self.mc.std(gpr.value, r.SPP.value, v * WORD + base_ofs)
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


class FieldOpAssembler(object):

    _mixin_ = True

    def _write_to_mem(self, value_loc, base_loc, ofs, size):
        if size.value == 8:
            if value_loc.is_fp_reg():
                if ofs.is_imm():
                    self.mc.stfd(value_loc.value, base_loc.value, ofs.value)
                else:
                    self.mc.stfdx(value_loc.value, base_loc.value, ofs.value)
            else:
                if ofs.is_imm():
                    self.mc.std(value_loc.value, base_loc.value, ofs.value)
                else:
                    self.mc.stdx(value_loc.value, base_loc.value, ofs.value)
        elif size.value == 4:
            if ofs.is_imm():
                self.mc.stw(value_loc.value, base_loc.value, ofs.value)
            else:
                self.mc.stwx(value_loc.value, base_loc.value, ofs.value)
        elif size.value == 2:
            if ofs.is_imm():
                self.mc.sth(value_loc.value, base_loc.value, ofs.value)
            else:
                self.mc.sthx(value_loc.value, base_loc.value, ofs.value)
        elif size.value == 1:
            if ofs.is_imm():
                self.mc.stb(value_loc.value, base_loc.value, ofs.value)
            else:
                self.mc.stbx(value_loc.value, base_loc.value, ofs.value)
        else:
            assert 0, "size not supported"

    def emit_setfield_gc(self, op, arglocs, regalloc):
        value_loc, base_loc, ofs, size = arglocs
        self._write_to_mem(value_loc, base_loc, ofs, size)

    emit_setfield_raw = emit_setfield_gc
    emit_zero_ptr_field = emit_setfield_gc

    def _load_from_mem(self, res, base_loc, ofs, size, signed):
        # res, base_loc, ofs, size and signed are all locations
        assert base_loc is not r.SCRATCH
        sign = signed.value
        if size.value == 8:
            if res.is_fp_reg():
                if ofs.is_imm():
                    self.mc.lfd(res.value, base_loc.value, ofs.value)
                else:
                    self.mc.lfdx(res.value, base_loc.value, ofs.value)
            else:
                if ofs.is_imm():
                    self.mc.ld(res.value, base_loc.value, ofs.value)
                else:
                    self.mc.ldx(res.value, base_loc.value, ofs.value)
        elif size.value == 4:
            if IS_PPC_64 and sign:
                if ofs.is_imm():
                    self.mc.lwa(res.value, base_loc.value, ofs.value)
                else:
                    self.mc.lwax(res.value, base_loc.value, ofs.value)
            else:
                if ofs.is_imm():
                    self.mc.lwz(res.value, base_loc.value, ofs.value)
                else:
                    self.mc.lwzx(res.value, base_loc.value, ofs.value)
        elif size.value == 2:
            if sign:
                if ofs.is_imm():
                    self.mc.lha(res.value, base_loc.value, ofs.value)
                else:
                    self.mc.lhax(res.value, base_loc.value, ofs.value)
            else:
                if ofs.is_imm():
                    self.mc.lhz(res.value, base_loc.value, ofs.value)
                else:
                    self.mc.lhzx(res.value, base_loc.value, ofs.value)
        elif size.value == 1:
            if ofs.is_imm():
                self.mc.lbz(res.value, base_loc.value, ofs.value)
            else:
                self.mc.lbzx(res.value, base_loc.value, ofs.value)
            if sign:
                self.mc.extsb(res.value, res.value)
        else:
            assert 0, "size not supported"

    def emit_getfield_gc(self, op, arglocs, regalloc):
        base_loc, ofs, res, size, sign = arglocs
        self._load_from_mem(res, base_loc, ofs, size, sign)

    emit_getfield_raw = emit_getfield_gc
    emit_getfield_raw_pure = emit_getfield_gc
    emit_getfield_gc_pure = emit_getfield_gc

    SIZE2SCALE = dict([(1<<_i, _i) for _i in range(32)])

    def _multiply_by_constant(self, loc, multiply_by, scratch_loc):
        if multiply_by == 1:
            return loc
        try:
            scale = self.SIZE2SCALE[multiply_by]
        except KeyError:
            if _check_imm_arg(multiply_by):
                self.mc.mulli(scratch_loc.value, loc.value, multiply_by)
            else:
                self.mc.load_imm(scratch_loc.value, multiply_by)
                if IS_PPC_32:
                    self.mc.mullw(scratch_loc.value, loc.value,
                                  scratch_loc.value)
                else:
                    self.mc.mulld(scratch_loc.value, loc.value,
                                  scratch_loc.value)
        else:
            self.mc.sldi(scratch_loc.value, loc.value, scale)
        return scratch_loc

    def _apply_scale(self, ofs, index_loc, itemsize):
        # For arrayitem and interiorfield reads and writes: this returns an
        # offset suitable for use in ld/ldx or similar instructions.
        # The result will be either the register r2 or a 16-bit immediate.
        # The arguments stand for "ofs + index_loc * itemsize",
        # with the following constrains:
        assert ofs.is_imm()                # must be an immediate...
        assert _check_imm_arg(ofs.getint())   # ...that fits 16 bits
        assert index_loc is not r.SCRATCH2 # can be a reg or imm (any size)
        assert itemsize.is_imm()           # must be an immediate (any size)

        multiply_by = itemsize.value
        offset = ofs.getint()
        if index_loc.is_imm():
            offset += index_loc.getint() * multiply_by
            if _check_imm_arg(offset):
                return imm(offset)
            else:
                self.mc.load_imm(r.SCRATCH2, offset)
                return r.SCRATCH2
        else:
            index_loc = self._multiply_by_constant(index_loc, multiply_by,
                                                   r.SCRATCH2)
            # here, the new index_loc contains 'index_loc * itemsize'.
            # If offset != 0 then we have to add it here.  Note that
            # mc.addi() would not be valid with operand r0.
            if offset != 0:
                self.mc.addi(r.SCRATCH2.value, index_loc.value, offset)
                index_loc = r.SCRATCH2
            return index_loc

    def emit_getinteriorfield_gc(self, op, arglocs, regalloc):
        (base_loc, index_loc, res_loc, ofs_loc,
            itemsize, fieldsize, fieldsign) = arglocs
        ofs_loc = self._apply_scale(ofs_loc, index_loc, itemsize)
        self._load_from_mem(res_loc, base_loc, ofs_loc, fieldsize, fieldsign)

    emit_getinteriorfield_raw = emit_getinteriorfield_gc

    def emit_setinteriorfield_gc(self, op, arglocs, regalloc):
        (base_loc, index_loc, value_loc, ofs_loc,
            itemsize, fieldsize) = arglocs
        ofs_loc = self._apply_scale(ofs_loc, index_loc, itemsize)
        self._write_to_mem(value_loc, base_loc, ofs_loc, fieldsize)

    emit_setinteriorfield_raw = emit_setinteriorfield_gc

    def emit_arraylen_gc(self, op, arglocs, regalloc):
        res, base_loc, ofs = arglocs
        self.mc.load(res.value, base_loc.value, ofs.value)

    emit_setarrayitem_gc = emit_setinteriorfield_gc
    emit_setarrayitem_raw = emit_setarrayitem_gc

    emit_getarrayitem_gc = emit_getinteriorfield_gc
    emit_getarrayitem_raw = emit_getarrayitem_gc
    emit_getarrayitem_gc_pure = emit_getarrayitem_gc

    emit_raw_store = emit_setarrayitem_gc
    emit_raw_load = emit_getarrayitem_gc

    def _copy_in_scratch2(self, loc):
        if loc.is_imm():
            self.mc.li(r.SCRATCH2.value, loc.value)
        elif loc is not r.SCRATCH2:
            self.mc.mr(r.SCRATCH2.value, loc.value)
        return r.SCRATCH2

    def emit_zero_array(self, op, arglocs, regalloc):
        base_loc, startindex_loc, length_loc, ofs_loc, itemsize_loc = arglocs

        # assume that an array where an item size is N:
        # * if N is even, then all items are aligned to a multiple of 2
        # * if N % 4 == 0, then all items are aligned to a multiple of 4
        # * if N % 8 == 0, then all items are aligned to a multiple of 8
        itemsize = itemsize_loc.getint()
        if itemsize & 1:
            stepsize = 1
            stXux = self.mc.stbux
            stXu = self.mc.stbu
            stX  = self.mc.stb
        elif itemsize & 2:
            stepsize = 2
            stXux = self.mc.sthux
            stXu = self.mc.sthu
            stX  = self.mc.sth
        elif (itemsize & 4) or IS_PPC_32:
            stepsize = 4
            stXux = self.mc.stwux
            stXu = self.mc.stwu
            stX  = self.mc.stw
        else:
            stepsize = WORD
            stXux = self.mc.stdux
            stXu = self.mc.stdu
            stX  = self.mc.std

        repeat_factor = itemsize // stepsize
        if repeat_factor != 1:
            # This is only for itemsize not in (1, 2, 4, WORD).
            # Include the repeat_factor inside length_loc if it is a constant
            if length_loc.is_imm():
                length_loc = imm(length_loc.value * repeat_factor)
                repeat_factor = 1     # included

        unroll = -1
        if length_loc.is_imm():
            if length_loc.value <= 8:
                unroll = length_loc.value
                if unroll <= 0:
                    return     # nothing to do

        ofs_loc = self._apply_scale(ofs_loc, startindex_loc, itemsize_loc)
        ofs_loc = self._copy_in_scratch2(ofs_loc)

        if unroll > 0:
            assert repeat_factor == 1
            self.mc.li(r.SCRATCH.value, 0)
            stXux(r.SCRATCH.value, ofs_loc.value, base_loc.value)
            for i in range(1, unroll):
                stX(r.SCRATCH.value, ofs_loc.value, i * stepsize)

        else:
            if length_loc.is_imm():
                self.mc.load_imm(r.SCRATCH, length_loc.value)
                length_loc = r.SCRATCH
                jz_location = -1
                assert repeat_factor == 1
            else:
                self.mc.cmp_op(0, length_loc.value, 0, imm=True)
                jz_location = self.mc.currpos()
                self.mc.trap()
                length_loc = self._multiply_by_constant(length_loc,
                                                        repeat_factor,
                                                        r.SCRATCH)
            self.mc.mtctr(length_loc.value)
            self.mc.li(r.SCRATCH.value, 0)

            stXux(r.SCRATCH.value, ofs_loc.value, base_loc.value)
            bdz_location = self.mc.currpos()
            self.mc.trap()

            loop_location = self.mc.currpos()
            stXu(r.SCRATCH.value, ofs_loc.value, stepsize)
            self.mc.bdnz(loop_location - self.mc.currpos())

            pmc = OverwritingBuilder(self.mc, bdz_location, 1)
            pmc.bdz(self.mc.currpos() - bdz_location)
            pmc.overwrite()

            if jz_location != -1:
                pmc = OverwritingBuilder(self.mc, jz_location, 1)
                pmc.ble(self.mc.currpos() - jz_location)    # !GT
                pmc.overwrite()

class StrOpAssembler(object):

    _mixin_ = True

    emit_strlen = FieldOpAssembler.emit_getfield_gc
    emit_strgetitem = FieldOpAssembler.emit_getarrayitem_gc
    emit_strsetitem = FieldOpAssembler.emit_setarrayitem_gc

    def emit_copystrcontent(self, op, arglocs, regalloc):
        self._emit_copycontent(arglocs, is_unicode=False)

    def emit_copyunicodecontent(self, op, arglocs, regalloc):
        self._emit_copycontent(arglocs, is_unicode=True)

    def _emit_load_for_copycontent(self, dst, src_ptr, src_ofs, scale):
        if src_ofs.is_imm():
            value = src_ofs.value << scale
            if value < 32768:
                self.mc.addi(dst.value, src_ptr.value, value)
            else:
                self.mc.load_imm(dst, value)
                self.mc.add(dst.value, src_ptr.value, dst.value)
        elif scale == 0:
            self.mc.add(dst.value, src_ptr.value, src_ofs.value)
        else:
            self.mc.sldi(dst.value, src_ofs.value, scale)
            self.mc.add(dst.value, src_ptr.value, dst.value)

    def _emit_copycontent(self, arglocs, is_unicode):
        [src_ptr_loc, dst_ptr_loc,
         src_ofs_loc, dst_ofs_loc, length_loc] = arglocs

        if is_unicode:
            basesize, itemsize, _ = symbolic.get_array_token(rstr.UNICODE,
                                        self.cpu.translate_support_code)
            if   itemsize == 2: scale = 1
            elif itemsize == 4: scale = 2
            else: raise AssertionError
        else:
            basesize, itemsize, _ = symbolic.get_array_token(rstr.STR,
                                        self.cpu.translate_support_code)
            assert itemsize == 1
            scale = 0

        self._emit_load_for_copycontent(r.r0, src_ptr_loc, src_ofs_loc, scale)
        self._emit_load_for_copycontent(r.r2, dst_ptr_loc, dst_ofs_loc, scale)

        if length_loc.is_imm():
            length = length_loc.getint()
            self.mc.load_imm(r.r5, length << scale)
        else:
            if scale > 0:
                self.mc.sldi(r.r5.value, length_loc.value, scale)
            elif length_loc is not r.r5:
                self.mc.mr(r.r5.value, length_loc.value)

        self.mc.mr(r.r4.value, r.r0.value)
        self.mc.addi(r.r4.value, r.r4.value, basesize)
        self.mc.addi(r.r3.value, r.r2.value, basesize)

        cb = callbuilder.CallBuilder(self, imm(self.memcpy_addr),
                                     [r.r3, r.r4, r.r5], None)
        cb.emit()


class UnicodeOpAssembler(object):

    _mixin_ = True

    emit_unicodelen = FieldOpAssembler.emit_getfield_gc
    emit_unicodegetitem = FieldOpAssembler.emit_getarrayitem_gc
    emit_unicodesetitem = FieldOpAssembler.emit_setarrayitem_gc


class AllocOpAssembler(object):

    _mixin_ = True

    def emit_call_malloc_gc(self, op, arglocs, regalloc):
        self.emit_call(op, arglocs, regalloc)
        self.propagate_memoryerror_if_r3_is_null()

    def emit_call_malloc_nursery(self, op, arglocs, regalloc):
        # registers r3 and r4 are allocated for this call
        assert len(arglocs) == 1
        size = arglocs[0].value
        gc_ll_descr = self.cpu.gc_ll_descr
        self.malloc_cond(
            gc_ll_descr.get_nursery_free_addr(),
            gc_ll_descr.get_nursery_top_addr(),
            size
            )

    def emit_debug_merge_point(self, op, arglocs, regalloc):
        pass

    emit_jit_debug = emit_debug_merge_point
    emit_keepalive = emit_debug_merge_point

    def _write_barrier_fastpath(self, mc, descr, arglocs, regalloc, array=False,
                                is_frame=False, align_stack=False):
        # Write code equivalent to write_barrier() in the GC: it checks
        # a flag in the object at arglocs[0], and if set, it calls a
        # helper piece of assembler.  The latter saves registers as needed
        # and call the function remember_young_pointer() from the GC.
        if we_are_translated():
            cls = self.cpu.gc_ll_descr.has_write_barrier_class()
            assert cls is not None and isinstance(descr, cls)
        #
        card_marking_mask = 0
        mask = descr.jit_wb_if_flag_singlebyte
        if array and descr.jit_wb_cards_set != 0:
            # assumptions the rest of the function depends on:
            assert (descr.jit_wb_cards_set_byteofs ==
                    descr.jit_wb_if_flag_byteofs)
            card_marking_mask = descr.jit_wb_cards_set_singlebyte
        #
        loc_base = arglocs[0]
        assert loc_base.is_reg()
        if is_frame:
            assert loc_base is r.SPP
        assert _check_imm_arg(descr.jit_wb_if_flag_byteofs)
        mc.lbz(r.SCRATCH2.value, loc_base.value, descr.jit_wb_if_flag_byteofs)
        mc.andix(r.SCRATCH.value, r.SCRATCH2.value, mask & 0xFF)

        jz_location = mc.get_relative_pos()
        mc.trap()        # patched later with 'beq'

        # for cond_call_gc_wb_array, also add another fast path:
        # if GCFLAG_CARDS_SET, then we can just set one bit and be done
        if card_marking_mask:
            # GCFLAG_CARDS_SET is in the same byte, loaded in r2 already
            mc.andix(r.SCRATCH.value, r.SCRATCH2.value,
                     card_marking_mask & 0xFF)
            js_location = mc.get_relative_pos()
            mc.trap()        # patched later with 'bne'
        else:
            js_location = 0

        # Write only a CALL to the helper prepared in advance, passing it as
        # argument the address of the structure we are writing into
        # (the first argument to COND_CALL_GC_WB).
        helper_num = (card_marking_mask != 0)
        if is_frame:
            helper_num = 4
        elif regalloc.fprm.reg_bindings:
            helper_num += 2
        if self.wb_slowpath[helper_num] == 0:    # tests only
            assert not we_are_translated()
            self.cpu.gc_ll_descr.write_barrier_descr = descr
            self._build_wb_slowpath(card_marking_mask != 0,
                                    bool(regalloc.fprm.reg_bindings))
            assert self.wb_slowpath[helper_num] != 0
        #
        if not is_frame:
            mc.mr(r.r0.value, loc_base.value)    # unusual argument location
        if is_frame and align_stack:
            XXXX
            mc.SUB_ri(esp.value, 16 - WORD) # erase the return address
        mc.load_imm(r.SCRATCH2, self.wb_slowpath[helper_num])
        mc.mtctr(r.SCRATCH2.value)
        mc.bctrl()
        if is_frame and align_stack:
            XXXX
            mc.ADD_ri(esp.value, 16 - WORD) # erase the return address

        if card_marking_mask:
            # The helper ends again with a check of the flag in the object.
            # So here, we can simply write again a beq, which will be
            # taken if GCFLAG_CARDS_SET is still not set.
            jns_location = mc.get_relative_pos()
            mc.trap()
            #
            # patch the 'bne' above
            currpos = mc.currpos()
            pmc = OverwritingBuilder(mc, js_location, 1)
            pmc.bne(currpos - js_location)
            pmc.overwrite()
            #
            # case GCFLAG_CARDS_SET: emit a few instructions to do
            # directly the card flag setting
            loc_index = arglocs[1]
            if loc_index.is_reg():

                tmp_loc = arglocs[2]
                n = descr.jit_wb_card_page_shift

                # compute in tmp_loc the byte offset:
                #     ~(index >> (card_page_shift + 3))   ('~' is 'not_' below)
                mc.srli_op(tmp_loc.value, loc_index.value, n + 3)

                # compute in r2 the index of the bit inside the byte:
                #     (index >> card_page_shift) & 7
                mc.rldicl(r.SCRATCH2.value, loc_index.value, 64 - n, 61)
                mc.li(r.SCRATCH.value, 1)
                mc.not_(tmp_loc.value, tmp_loc.value)

                # set r2 to 1 << r2
                mc.sl_op(r.SCRATCH2.value, r.SCRATCH.value, r.SCRATCH2.value)

                # set this bit inside the byte of interest
                mc.lbzx(r.SCRATCH.value, loc_base.value, tmp_loc.value)
                mc.or_(r.SCRATCH.value, r.SCRATCH.value, r.SCRATCH2.value)
                mc.stbx(r.SCRATCH.value, loc_base.value, tmp_loc.value)
                # done

            else:
                byte_index = loc_index.value >> descr.jit_wb_card_page_shift
                byte_ofs = ~(byte_index >> 3)
                byte_val = 1 << (byte_index & 7)
                assert _check_imm_arg(byte_ofs)

                mc.lbz(r.SCRATCH.value, loc_base.value, byte_ofs)
                mc.ori(r.SCRATCH.value, r.SCRATCH.value, byte_val)
                mc.stb(r.SCRATCH.value, loc_base.value, byte_ofs)
            #
            # patch the beq just above
            currpos = mc.currpos()
            pmc = OverwritingBuilder(mc, jns_location, 1)
            pmc.beq(currpos - jns_location)
            pmc.overwrite()

        # patch the JZ above
        currpos = mc.currpos()
        pmc = OverwritingBuilder(mc, jz_location, 1)
        pmc.beq(currpos - jz_location)
        pmc.overwrite()

    def emit_cond_call_gc_wb(self, op, arglocs, regalloc):
        self._write_barrier_fastpath(self.mc, op.getdescr(), arglocs, regalloc)

    def emit_cond_call_gc_wb_array(self, op, arglocs, regalloc):
        self._write_barrier_fastpath(self.mc, op.getdescr(), arglocs, regalloc,
                                     array=True)


class ForceOpAssembler(object):

    _mixin_ = True
    
    def emit_force_token(self, op, arglocs, regalloc):
        res_loc = arglocs[0]
        self.mc.mr(res_loc.value, r.SPP.value)

    def emit_call_assembler(self, op, arglocs, regalloc):
        if len(arglocs) == 3:
            [result_loc, argloc, vloc] = arglocs
        else:
            [result_loc, argloc] = arglocs
            vloc = imm(0)
        self._store_force_index(self._find_nearby_operation(regalloc, +1))
        # 'result_loc' is either r3 or f1
        self.call_assembler(op, argloc, vloc, result_loc, r.r3)

    imm = staticmethod(imm)   # for call_assembler()

    def _call_assembler_emit_call(self, addr, argloc, _):
        self.regalloc_mov(argloc, r.r3)
        self.mc.ld(r.r4.value, r.SP.value, THREADLOCAL_ADDR_OFFSET)

        cb = callbuilder.CallBuilder(self, addr, [r.r3, r.r4], r.r3)
        cb.emit()

    def _call_assembler_emit_helper_call(self, addr, arglocs, result_loc):
        cb = callbuilder.CallBuilder(self, addr, arglocs, result_loc)
        cb.emit()

    def _call_assembler_check_descr(self, value, tmploc):
        ofs = self.cpu.get_ofs_of_frame_field('jf_descr')
        self.mc.ld(r.r5.value, r.r3.value, ofs)
        if _check_imm_arg(value):
            self.mc.cmp_op(0, r.r5.value, value, imm=True)
        else:
            self.mc.load_imm(r.r4, value)
            self.mc.cmp_op(0, r.r5.value, r.r4.value, imm=False)
        jump_if_eq = self.mc.currpos()
        self.mc.nop()      # patched later
        return jump_if_eq

    def _call_assembler_patch_je(self, result_loc, je_location):
        jump_to_done = self.mc.currpos()
        self.mc.nop()      # patched later
        #
        currpos = self.mc.currpos()
        pmc = OverwritingBuilder(self.mc, je_location, 1)
        pmc.beq(currpos - je_location)
        pmc.overwrite()
        #
        return jump_to_done

    def _call_assembler_load_result(self, op, result_loc):
        if op.result is not None:
            # load the return value from the dead frame's value index 0
            kind = op.result.type
            descr = self.cpu.getarraydescr_for_frame(kind)
            ofs = self.cpu.unpack_arraydescr(descr)
            if kind == FLOAT:
                assert result_loc is r.f1
                self.mc.lfd(r.f1.value, r.r3.value, ofs)
            else:
                assert result_loc is r.r3
                self.mc.ld(r.r3.value, r.r3.value, ofs)

    def _call_assembler_patch_jmp(self, jmp_location):
        currpos = self.mc.currpos()
        pmc = OverwritingBuilder(self.mc, jmp_location, 1)
        pmc.b(currpos - jmp_location)
        pmc.overwrite()

    def redirect_call_assembler(self, oldlooptoken, newlooptoken):
        # some minimal sanity checking
        old_nbargs = oldlooptoken.compiled_loop_token._debug_nbargs
        new_nbargs = newlooptoken.compiled_loop_token._debug_nbargs
        assert old_nbargs == new_nbargs
        oldadr = oldlooptoken._ll_function_addr
        target = newlooptoken._ll_function_addr
        if IS_PPC_32 or not IS_BIG_ENDIAN:
            # we overwrite the instructions at the old _ll_function_addr
            # to start with a JMP to the new _ll_function_addr.
            # Ideally we should rather patch all existing CALLs, but well.
            mc = PPCBuilder()
            mc.b_abs(target)
            mc.copy_to_raw_memory(oldadr)
        else:
            # PPC64 big-endian trampolines are data so overwrite the code
            # address in the function descriptor at the old address.
            # Copy the whole 3-word trampoline, even though the other
            # words are always zero so far.
            odata = rffi.cast(rffi.CArrayPtr(lltype.Signed), oldadr)
            tdata = rffi.cast(rffi.CArrayPtr(lltype.Signed), target)
            odata[0] = tdata[0]
            odata[1] = tdata[1]
            odata[2] = tdata[2]


class OpAssembler(IntOpAssembler, GuardOpAssembler,
                  MiscOpAssembler, FieldOpAssembler,
                  StrOpAssembler, CallOpAssembler,
                  UnicodeOpAssembler, ForceOpAssembler,
                  AllocOpAssembler, FloatOpAssembler):

    def nop(self):
        self.mc.ori(0, 0, 0)

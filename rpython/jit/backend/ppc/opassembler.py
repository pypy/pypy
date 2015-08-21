from rpython.jit.backend.ppc.helper.assembler import (gen_emit_cmp_op,
                                                      gen_emit_unary_cmp_op)
from rpython.jit.backend.ppc.helper.regalloc import _check_imm_arg
import rpython.jit.backend.ppc.condition as c
import rpython.jit.backend.ppc.register as r
from rpython.jit.backend.ppc.locations import imm
from rpython.jit.backend.ppc.locations import imm as make_imm_loc
from rpython.jit.backend.ppc.arch import (IS_PPC_32, WORD,
                                          MAX_REG_PARAMS, MAX_FREG_PARAMS)

from rpython.jit.metainterp.history import (JitCellToken, TargetToken, Box,
                                            AbstractFailDescr, FLOAT, INT, REF)
from rpython.rlib.objectmodel import we_are_translated
from rpython.jit.backend.ppc.helper.assembler import (Saved_Volatiles)
from rpython.jit.backend.ppc.jump import remap_frame_layout
from rpython.jit.backend.ppc.codebuilder import (OverwritingBuilder, scratch_reg,
                                                 PPCBuilder, PPCGuardToken)
from rpython.jit.backend.ppc.regalloc import TempPtr, TempInt
from rpython.jit.backend.llsupport import symbolic
from rpython.jit.backend.llsupport.descr import InteriorFieldDescr
from rpython.jit.backend.llsupport.gcmap import allocate_gcmap
from rpython.rtyper.lltypesystem import rstr, rffi, lltype
from rpython.jit.metainterp.resoperation import rop

NO_FORCE_INDEX = -1

class IntOpAssembler(object):
        
    _mixin_ = True

    def emit_int_add(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        if l0.is_imm():
            self.mc.addi(res.value, l1.value, l0.value)
        elif l1.is_imm():
            self.mc.addi(res.value, l0.value, l1.value)
        else:
            self.mc.add(res.value, l0.value, l1.value)

    def emit_int_add_ovf(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        self.mc.addo(res.value, l0.value, l1.value)

    def emit_int_sub(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        if l0.is_imm():
            self.mc.subfic(res.value, l1.value, l0.value)
        elif l1.is_imm():
            self.mc.subi(res.value, l0.value, l1.value)
        else:
            self.mc.sub(res.value, l0.value, l1.value)
 
    def emit_int_sub_ovf(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        self.mc.subfo(res.value, l1.value, l0.value)

    def emit_int_mul(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        if l0.is_imm():
            self.mc.mulli(res.value, l1.value, l0.value)
        elif l1.is_imm():
            self.mc.mulli(res.value, l0.value, l1.value)
        elif IS_PPC_32:
            self.mc.mullw(res.value, l0.value, l1.value)
        else:
            self.mc.mulld(res.value, l0.value, l1.value)

    def emit_int_mul_ovf(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        if IS_PPC_32:
            self.mc.mullwo(res.value, l0.value, l1.value)
        else:
            self.mc.mulldo(res.value, l0.value, l1.value)

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

    emit_uint_lt = gen_emit_cmp_op(c.U_LT, signed=False)
    emit_uint_le = gen_emit_cmp_op(c.U_LE, signed=False)
    emit_uint_gt = gen_emit_cmp_op(c.U_GT, signed=False)
    emit_uint_ge = gen_emit_cmp_op(c.U_GE, signed=False)

    emit_int_is_zero = gen_emit_unary_cmp_op(c.IS_ZERO)
    emit_int_is_true = gen_emit_unary_cmp_op(c.IS_TRUE)

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

    def emit_math_sqrt(self, op, arglocs, regalloc):
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
        self.mc.stfd(temp_loc.value, r.SPP.value, FORCE_INDEX_OFS + WORD)
        self.mc.ld(res.value, r.SPP.value, FORCE_INDEX_OFS + WORD)

    def emit_cast_int_to_float(self, op, arglocs, regalloc):
        l0, temp_loc, res = arglocs
        self.mc.std(l0.value, r.SPP.value, FORCE_INDEX_OFS + WORD)
        self.mc.lfd(temp_loc.value, r.SPP.value, FORCE_INDEX_OFS + WORD)
        self.mc.fcfid(res.value, temp_loc.value)

    def emit_convert_float_bytes_to_longlong(self, op, arglocs, regalloc):
        l0, res = arglocs
        self.mc.stfd(l0.value, r.SPP.value, FORCE_INDEX_OFS + WORD)
        self.mc.ld(res.value, r.SPP.value, FORCE_INDEX_OFS + WORD)

    def emit_convert_longlong_bytes_to_float(self, op, arglocs, regalloc):
        l0, res = arglocs
        self.mc.std(l0.value, r.SPP.value, FORCE_INDEX_OFS + WORD)
        self.mc.lfd(res.value, r.SPP.value, FORCE_INDEX_OFS + WORD)

class GuardOpAssembler(object):

    _mixin_ = True

    def _emit_guard(self, op, arglocs, fcond, save_exc=False,
                    is_guard_not_invalidated=False,
                    is_guard_not_forced=False):
        pos = self.mc.currpos()
        self.mc.nop()     # has to be patched later on
        token = self.build_guard_token(op, arglocs[0].value, arglocs[1:],
                                       fcond, save_exc, is_guard_not_invalidated,
                                       is_guard_not_forced)
        self.pending_guards.append(token)

    def build_guard_token(self, op, frame_depth, arglocs, fcond, save_exc,
                          is_guard_not_invalidated=False,
                          is_guard_not_forced=False):
        descr = op.getdescr()
        offset = self.mc.currpos()
        gcmap = allocate_gcmap(self, frame_depth, JITFRAME_FIXED_SIZE)
        token = PPCGuardToken(self.cpu, gcmap, descr, op.getfailargs(),
                              arglocs, save_exc, frame_depth,
                              is_guard_not_invalidated, is_guard_not_forced)
        return token

    def emit_guard_true(self, op, arglocs, regalloc):
        l0 = arglocs[0]
        failargs = arglocs[1:]
        self.mc.cmp_op(0, l0.value, 0, imm=True)
        self._emit_guard(op, failargs, c.EQ)
        #                        #      ^^^^ If this condition is met,
        #                        #           then the guard fails.

    def emit_guard_false(self, op, arglocs, regalloc):
        l0 = arglocs[0]
        failargs = arglocs[1:]
        self.mc.cmp_op(0, l0.value, 0, imm=True)
        self._emit_guard(op, failargs, c.NE)

    # TODO - Evaluate whether this can be done with 
    #        SO bit instead of OV bit => usage of CR
    #        instead of XER could be more efficient
    def _emit_ovf_guard(self, op, arglocs, cond):
        # move content of XER to GPR
        with scratch_reg(self.mc):
            self.mc.mfspr(r.SCRATCH.value, 1)
            # shift and mask to get comparison result
            self.mc.rlwinm(r.SCRATCH.value, r.SCRATCH.value, 1, 0, 0)
            self.mc.cmp_op(0, r.SCRATCH.value, 0, imm=True)
        self._emit_guard(op, arglocs, cond)

    def emit_guard_no_overflow(self, op, arglocs, regalloc):
        self._emit_ovf_guard(op, arglocs, c.NE)

    def emit_guard_overflow(self, op, arglocs, regalloc):
        self._emit_ovf_guard(op, arglocs, c.EQ)

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
        self._emit_guard(op, failargs, c.NE)

    emit_guard_nonnull = emit_guard_true
    emit_guard_isnull = emit_guard_false

    def emit_guard_class(self, op, arglocs, regalloc):
        self._cmp_guard_class(op, arglocs, regalloc)
        self._emit_guard(op, arglocs[3:], c.NE, save_exc=False)

    def emit_guard_nonnull_class(self, op, arglocs, regalloc):
        self.mc.cmp_op(0, arglocs[0].value, 1, imm=True, signed=False)
        patch_pos = self.mc.currpos()
        self.mc.nop()
        self._cmp_guard_class(op, arglocs, regalloc)
        pmc = OverwritingBuilder(self.mc, patch_pos, 1)
        pmc.bc(12, 0, self.mc.currpos() - patch_pos)
        pmc.overwrite()
        self._emit_guard(op, arglocs[3:], c.NE, save_exc=False)

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
            # it would be at offset 2 (32 bit) or 4 (64 bit) on a
            # big-endian machine.
            with scratch_reg(self.mc):
                if IS_PPC_32:
                    self.mc.lhz(r.SCRATCH.value, locs[0].value, 2)
                else:
                    self.mc.lwz(r.SCRATCH.value, locs[0].value, 4)
                self.mc.cmp_op(0, r.SCRATCH.value, typeid.value, imm=typeid.is_imm())

    def emit_guard_not_invalidated(self, op, locs, regalloc):
        return self._emit_guard(op, locs, c.EQ, is_guard_not_invalidated=True)

class MiscOpAssembler(object):

    _mixin_ = True

    def emit_increment_debug_counter(self, op, arglocs, regalloc):
        [addr_loc, value_loc] = arglocs
        self.mc.load(value_loc.value, addr_loc.value, 0)
        self.mc.addi(value_loc.value, value_loc.value, 1)
        self.mc.store(value_loc.value, addr_loc.value, 0)

    def emit_finish(self, op, arglocs, regalloc):
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        if len(arglocs) == 2:
            [return_val, fail_descr_loc] = arglocs
            self.mc.std(return_val.value, r.SPP.value, base_ofs)
        else:
            [fail_descr_loc] = arglocs

        ofs = self.cpu.get_ofs_of_frame_field('jf_descr')
        self.mc.load_imm(r.r5, fail_descr_loc.getint())
        self.mc.std(r.r5.value, r.SPP.value, ofs)

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
        self.regalloc_mov(argloc, resloc)

    emit_cast_ptr_to_int = emit_same_as
    emit_cast_int_to_ptr = emit_same_as

    def emit_guard_no_exception(self, op, arglocs, regalloc):
        loc = arglocs[0]
        failargs = arglocs[1:]

        self.mc.load(loc.value, loc.value, 0)
        self.mc.cmp_op(0, loc.value, 0, imm=True)

        self._emit_guard(op, failargs, c.NE, save_exc=True)

    def emit_guard_exception(self, op, arglocs, regalloc):
        loc, loc1, resloc, pos_exc_value, pos_exception = arglocs[:5]
        failargs = arglocs[5:]
        self.mc.load_imm(loc1, pos_exception.value)

        with scratch_reg(self.mc):
            self.mc.load(r.SCRATCH.value, loc1.value, 0)
            self.mc.cmp_op(0, r.SCRATCH.value, loc.value)

        self._emit_guard(op, failargs, c.NE, save_exc=True)
        self.mc.load_imm(loc, pos_exc_value.value)

        if resloc:
            self.mc.load(resloc.value, loc.value, 0)

        with scratch_reg(self.mc):
            self.mc.load_imm(r.SCRATCH, 0)
            self.mc.store(r.SCRATCH.value, loc.value, 0)
            self.mc.store(r.SCRATCH.value, loc1.value, 0)

    def emit_call(self, op, arglocs, regalloc, force_index=NO_FORCE_INDEX):
        if force_index == NO_FORCE_INDEX:
            force_index = self.write_new_force_index()
        resloc = arglocs[0]
        adr = arglocs[1]
        arglist = arglocs[2:]
        descr = op.getdescr()
        size = descr.get_result_size()
        signed = descr.is_result_signed()
        self._emit_call(force_index, adr, arglist, resloc, (size, signed))

    def _emit_call(self, force_index, adr, arglocs,
                   result=None, result_info=(-1,-1)):
        n_args = len(arglocs)

        # collect variables that need to go in registers
        # and the registers they will be stored in 
        num = 0
        fpnum = 0
        count = 0
        non_float_locs = []
        non_float_regs = []
        float_locs = []
        float_regs = []
        stack_args = []
        float_stack_arg = False
        for i in range(n_args):
            arg = arglocs[i]

            if arg.type == FLOAT:
                if fpnum < MAX_FREG_PARAMS:
                    fpreg = r.PARAM_FPREGS[fpnum]
                    float_locs.append(arg)
                    float_regs.append(fpreg)
                    fpnum += 1
                    # XXX Duplicate float arguments in GPR slots
                    if num < MAX_REG_PARAMS:
                        num += 1
                    else:
                        stack_args.append(arg)
                else:
                    stack_args.append(arg)
            else:
                if num < MAX_REG_PARAMS:
                    reg = r.PARAM_REGS[num]
                    non_float_locs.append(arg)
                    non_float_regs.append(reg)
                    num += 1
                else:
                    stack_args.append(arg)
                    float_stack_arg = True

        if adr in non_float_regs:
            non_float_locs.append(adr)
            non_float_regs.append(r.r11)
            adr = r.r11

        # compute maximum of parameters passed
        self.max_stack_params = max(self.max_stack_params, len(stack_args))

        # compute offset at which parameters are stored
        if IS_PPC_32:
            param_offset = BACKCHAIN_SIZE * WORD
        else:
            # space for first 8 parameters
            param_offset = ((BACKCHAIN_SIZE + MAX_REG_PARAMS) * WORD)

        with scratch_reg(self.mc):
            if float_stack_arg:
                self.mc.stfd(r.f0.value, r.SPP.value, FORCE_INDEX_OFS + WORD)
            for i, arg in enumerate(stack_args):
                offset = param_offset + i * WORD
                if arg is not None:
                    if arg.type == FLOAT:
                        self.regalloc_mov(arg, r.f0)
                        self.mc.stfd(r.f0.value, r.SP.value, offset)
                    else:
                        self.regalloc_mov(arg, r.SCRATCH)
                        self.mc.store(r.SCRATCH.value, r.SP.value, offset)
            if float_stack_arg:
                self.mc.lfd(r.f0.value, r.SPP.value, FORCE_INDEX_OFS + WORD)

        # remap values stored in core registers
        remap_frame_layout(self, float_locs, float_regs, r.f0)
        remap_frame_layout(self, non_float_locs, non_float_regs, r.SCRATCH)

        # the actual call
        if adr.is_imm():
            self.mc.call(adr.value)
        elif adr.is_stack():
            self.regalloc_mov(adr, r.SCRATCH)
            self.mc.call_register(r.SCRATCH)
        elif adr.is_reg():
            self.mc.call_register(adr)
        else:
            assert 0, "should not reach here"

        self.mark_gc_roots(force_index)
        # ensure the result is wellformed and stored in the correct location
        if result is not None and result_info != (-1, -1):
            self._ensure_result_bit_extension(result, result_info[0],
                                                      result_info[1])

class FieldOpAssembler(object):

    _mixin_ = True

    def emit_setfield_gc(self, op, arglocs, regalloc):
        value_loc, base_loc, ofs, size = arglocs
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

    emit_setfield_raw = emit_setfield_gc

    def emit_getfield_gc(self, op, arglocs, regalloc):
        base_loc, ofs, res, size = arglocs
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
            if ofs.is_imm():
                self.mc.lwz(res.value, base_loc.value, ofs.value)
            else:
                self.mc.lwzx(res.value, base_loc.value, ofs.value)
        elif size.value == 2:
            if ofs.is_imm():
                self.mc.lhz(res.value, base_loc.value, ofs.value)
            else:
                self.mc.lhzx(res.value, base_loc.value, ofs.value)
        elif size.value == 1:
            if ofs.is_imm():
                self.mc.lbz(res.value, base_loc.value, ofs.value)
            else:
                self.mc.lbzx(res.value, base_loc.value, ofs.value)
        else:
            assert 0, "size not supported"

        signed = op.getdescr().is_field_signed()
        if signed:
            self._ensure_result_bit_extension(res, size.value, signed)

    emit_getfield_raw = emit_getfield_gc
    emit_getfield_raw_pure = emit_getfield_gc
    emit_getfield_gc_pure = emit_getfield_gc

    def emit_getinteriorfield_gc(self, op, arglocs, regalloc):
        (base_loc, index_loc, res_loc,
            ofs_loc, ofs, itemsize, fieldsize) = arglocs
        with scratch_reg(self.mc):
            if _check_imm_arg(itemsize.value):
                self.mc.mulli(r.SCRATCH.value, index_loc.value, itemsize.value)
            else:
                self.mc.load_imm(r.SCRATCH, itemsize.value)
                self.mc.mullw(r.SCRATCH.value, index_loc.value, r.SCRATCH.value)
            descr = op.getdescr()
            assert isinstance(descr, InteriorFieldDescr)
            signed = descr.fielddescr.is_field_signed()
            if ofs.value > 0:
                if ofs_loc.is_imm():
                    self.mc.addic(r.SCRATCH.value, r.SCRATCH.value, ofs_loc.value)
                else:
                    self.mc.add(r.SCRATCH.value, r.SCRATCH.value, ofs_loc.value)

            if fieldsize.value == 8:
                if res_loc.is_fp_reg():
                    self.mc.lfdx(res_loc.value, base_loc.value, r.SCRATCH.value)
                else:
                    self.mc.ldx(res_loc.value, base_loc.value, r.SCRATCH.value)
            elif fieldsize.value == 4:
                self.mc.lwzx(res_loc.value, base_loc.value, r.SCRATCH.value)
                if signed:
                    self.mc.extsw(res_loc.value, res_loc.value)
            elif fieldsize.value == 2:
                self.mc.lhzx(res_loc.value, base_loc.value, r.SCRATCH.value)
                if signed:
                    self.mc.extsh(res_loc.value, res_loc.value)
            elif fieldsize.value == 1:
                self.mc.lbzx(res_loc.value, base_loc.value, r.SCRATCH.value)
                if signed:
                    self.mc.extsb(res_loc.value, res_loc.value)
            else:
                assert 0

    emit_getinteriorfield_raw = emit_getinteriorfield_gc

    def emit_setinteriorfield_gc(self, op, arglocs, regalloc):
        (base_loc, index_loc, value_loc,
            ofs_loc, ofs, itemsize, fieldsize) = arglocs
        with scratch_reg(self.mc):
            if _check_imm_arg(itemsize.value):
                self.mc.mulli(r.SCRATCH.value, index_loc.value, itemsize.value)
            else:
                self.mc.load_imm(r.SCRATCH, itemsize.value)
                self.mc.mullw(r.SCRATCH.value, index_loc.value, r.SCRATCH.value)
            if ofs.value > 0:
                if ofs_loc.is_imm():
                    self.mc.addic(r.SCRATCH.value, r.SCRATCH.value, ofs_loc.value)
                else:
                    self.mc.add(r.SCRATCH.value, r.SCRATCH.value, ofs_loc.value)
            if fieldsize.value == 8:
                if value_loc.is_fp_reg():
                    self.mc.stfdx(value_loc.value, base_loc.value, r.SCRATCH.value)
                else:
                    self.mc.stdx(value_loc.value, base_loc.value, r.SCRATCH.value)
            elif fieldsize.value == 4:
                self.mc.stwx(value_loc.value, base_loc.value, r.SCRATCH.value)
            elif fieldsize.value == 2:
                self.mc.sthx(value_loc.value, base_loc.value, r.SCRATCH.value)
            elif fieldsize.value == 1:
                self.mc.stbx(value_loc.value, base_loc.value, r.SCRATCH.value)
            else:
                assert 0

    emit_setinteriorfield_raw = emit_setinteriorfield_gc

class ArrayOpAssembler(object):
    
    _mixin_ = True

    def emit_arraylen_gc(self, op, arglocs, regalloc):
        res, base_loc, ofs = arglocs
        self.mc.load(res.value, base_loc.value, ofs.value)

    def emit_setarrayitem_gc(self, op, arglocs, regalloc):
        value_loc, base_loc, ofs_loc, scratch_loc, scale, ofs = arglocs
        assert ofs_loc.is_reg()

        if scale.value > 0:
            #scale_loc = r.SCRATCH
            scale_loc = scratch_loc
            if IS_PPC_32:
                self.mc.slwi(scale_loc.value, ofs_loc.value, scale.value)
            else:
                self.mc.sldi(scale_loc.value, ofs_loc.value, scale.value)
        else:
            scale_loc = ofs_loc

        # add the base offset
        if ofs.value > 0:
            self.mc.addi(r.SCRATCH.value, scale_loc.value, ofs.value)
            scale_loc = r.SCRATCH

        if scale.value == 3:
            if value_loc.is_fp_reg():
                self.mc.stfdx(value_loc.value, base_loc.value, scale_loc.value)
            else:
                self.mc.stdx(value_loc.value, base_loc.value, scale_loc.value)
        elif scale.value == 2:
            self.mc.stwx(value_loc.value, base_loc.value, scale_loc.value)
        elif scale.value == 1:
            self.mc.sthx(value_loc.value, base_loc.value, scale_loc.value)
        elif scale.value == 0:
            self.mc.stbx(value_loc.value, base_loc.value, scale_loc.value)
        else:
            assert 0, "scale %s not supported" % (scale.value)

    emit_setarrayitem_raw = emit_setarrayitem_gc

    def _write_to_mem(self, value_loc, base_loc, ofs_loc, scale):
        if scale.value == 3:
            if value_loc.is_fp_reg():
                self.mc.stfdx(value_loc.value, base_loc.value, ofs_loc.value)
            else:
                self.mc.stdx(value_loc.value, base_loc.value, ofs_loc.value)
        elif scale.value == 2:
            self.mc.stwx(value_loc.value, base_loc.value, ofs_loc.value)
        elif scale.value == 1:
            self.mc.sthx(value_loc.value, base_loc.value, ofs_loc.value)
        elif scale.value == 0:
            self.mc.stbx(value_loc.value, base_loc.value, ofs_loc.value)
        else:
            assert 0

    def emit_raw_store(self, op, arglocs, regalloc):
        value_loc, base_loc, ofs_loc, scale, ofs = arglocs
        assert ofs_loc.is_reg()
        self._write_to_mem(value_loc, base_loc, ofs_loc, scale)

    def emit_getarrayitem_gc(self, op, arglocs, regalloc):
        res, base_loc, ofs_loc, scratch_loc, scale, ofs = arglocs
        assert ofs_loc.is_reg()
        signed = op.getdescr().is_item_signed()

        if scale.value > 0:
            scale_loc = scratch_loc
            if IS_PPC_32:
                self.mc.slwi(scale_loc.value, ofs_loc.value, scale.value)
            else:
                self.mc.sldi(scale_loc.value, ofs_loc.value, scale.value)
        else:
            scale_loc = ofs_loc

        # add the base offset
        if ofs.value > 0:
            self.mc.addi(r.SCRATCH.value, scale_loc.value, ofs.value)
            scale_loc = r.SCRATCH

        if scale.value == 3:
            if res.is_fp_reg():
                self.mc.lfdx(res.value, base_loc.value, scale_loc.value)
            else:
                self.mc.ldx(res.value, base_loc.value, scale_loc.value)
        elif scale.value == 2:
            self.mc.lwzx(res.value, base_loc.value, scale_loc.value)
            if signed:
                self.mc.extsw(res.value, res.value)
        elif scale.value == 1:
            self.mc.lhzx(res.value, base_loc.value, scale_loc.value)
            if signed:
                self.mc.extsh(res.value, res.value)
        elif scale.value == 0:
            self.mc.lbzx(res.value, base_loc.value, scale_loc.value)
            if signed:
                self.mc.extsb(res.value, res.value)
        else:
            assert 0

    emit_getarrayitem_raw = emit_getarrayitem_gc
    emit_getarrayitem_gc_pure = emit_getarrayitem_gc

    def _load_from_mem(self, res_loc, base_loc, ofs_loc, scale, signed=False):
        if scale.value == 3:
            if res_loc.is_fp_reg():
                self.mc.lfdx(res_loc.value, base_loc.value, ofs_loc.value)
            else:
                self.mc.ldx(res_loc.value, base_loc.value, ofs_loc.value)
        elif scale.value == 2:
            self.mc.lwzx(res_loc.value, base_loc.value, ofs_loc.value)
            if signed:
                self.mc.extsw(res_loc.value, res_loc.value)
        elif scale.value == 1:
            self.mc.lhzx(res_loc.value, base_loc.value, ofs_loc.value)
            if signed:
                self.mc.extsh(res_loc.value, res_loc.value)
        elif scale.value == 0:
            self.mc.lbzx(res_loc.value, base_loc.value, ofs_loc.value)
            if signed:
                self.mc.extsb(res_loc.value, res_loc.value)
        else:
            assert 0

    def emit_raw_load(self, op, arglocs, regalloc):
        res_loc, base_loc, ofs_loc, scale, ofs = arglocs
        assert ofs_loc.is_reg()
        # no base offset
        assert ofs.value == 0
        signed = op.getdescr().is_item_signed()
        self._load_from_mem(res_loc, base_loc, ofs_loc, scale, signed)

class StrOpAssembler(object):

    _mixin_ = True

    def emit_strlen(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        if l1.is_imm():
            self.mc.load(res.value, l0.value, l1.getint())
        else:
            self.mc.loadx(res.value, l0.value, l1.value)

    def emit_strgetitem(self, op, arglocs, regalloc):
        res, base_loc, ofs_loc, basesize = arglocs
        if ofs_loc.is_imm():
            self.mc.addi(res.value, base_loc.value, ofs_loc.getint())
        else:
            self.mc.add(res.value, base_loc.value, ofs_loc.value)
        self.mc.lbz(res.value, res.value, basesize.value)

    def emit_strsetitem(self, op, arglocs, regalloc):
        value_loc, base_loc, ofs_loc, temp_loc, basesize = arglocs
        if ofs_loc.is_imm():
            self.mc.addi(temp_loc.value, base_loc.value, ofs_loc.getint())
        else:
            self.mc.add(temp_loc.value, base_loc.value, ofs_loc.value)
        self.mc.stb(value_loc.value, temp_loc.value, basesize.value)

    #from ../x86/regalloc.py:928 ff.
    def emit_copystrcontent(self, op, arglocs, regalloc):
        assert len(arglocs) == 0
        self._emit_copystrcontent(op, regalloc, is_unicode=False)

    def emit_copyunicodecontent(self, op, arglocs, regalloc):
        assert len(arglocs) == 0
        self._emit_copystrcontent(op, regalloc, is_unicode=True)

    def _emit_copystrcontent(self, op, regalloc, is_unicode):
        # compute the source address
        args = op.getarglist()
        base_loc = regalloc._ensure_value_is_boxed(args[0], args)
        ofs_loc = regalloc._ensure_value_is_boxed(args[2], args)
        assert args[0] is not args[1]    # forbidden case of aliasing
        regalloc.possibly_free_var(args[0])
        if args[3] is not args[2] is not args[4]:  # MESS MESS MESS: don't free
            regalloc.possibly_free_var(args[2])     # it if ==args[3] or args[4]
        srcaddr_box = TempPtr()
        forbidden_vars = [args[1], args[3], args[4], srcaddr_box]
        srcaddr_loc = regalloc.force_allocate_reg(srcaddr_box)
        self._gen_address_inside_string(base_loc, ofs_loc, srcaddr_loc,
                                        is_unicode=is_unicode)

        # compute the destination address
        forbidden_vars = [args[4], args[3], srcaddr_box]
        dstaddr_box = TempPtr()
        dstaddr_loc = regalloc.force_allocate_reg(dstaddr_box)
        forbidden_vars.append(dstaddr_box)
        base_loc = regalloc._ensure_value_is_boxed(args[1], forbidden_vars)
        ofs_loc = regalloc._ensure_value_is_boxed(args[3], forbidden_vars)
        assert base_loc.is_reg()
        assert ofs_loc.is_reg()
        regalloc.possibly_free_var(args[1])
        if args[3] is not args[4]:     # more of the MESS described above
            regalloc.possibly_free_var(args[3])
        regalloc.free_temp_vars()
        self._gen_address_inside_string(base_loc, ofs_loc, dstaddr_loc,
                                        is_unicode=is_unicode)

        # compute the length in bytes
        forbidden_vars = [srcaddr_box, dstaddr_box]
        if isinstance(args[4], Box):
            length_box = args[4]
            length_loc = regalloc.make_sure_var_in_reg(args[4], forbidden_vars)
        else:
            length_box = TempInt()
            length_loc = regalloc.force_allocate_reg(length_box, forbidden_vars)
            imm = regalloc.convert_to_imm(args[4])
            self.load(length_loc, imm)
        if is_unicode:
            bytes_box = TempPtr()
            bytes_loc = regalloc.force_allocate_reg(bytes_box, forbidden_vars)
            scale = self._get_unicode_item_scale()
            assert length_loc.is_reg()
            with scratch_reg(self.mc):
                self.mc.load_imm(r.SCRATCH, 1 << scale)
                if IS_PPC_32:
                    self.mc.mullw(bytes_loc.value, r.SCRATCH.value, length_loc.value)
                else:
                    self.mc.mulld(bytes_loc.value, r.SCRATCH.value, length_loc.value)
            length_box = bytes_box
            length_loc = bytes_loc
        # call memcpy()
        regalloc.before_call()
        imm_addr = make_imm_loc(self.memcpy_addr)
        self._emit_call(NO_FORCE_INDEX, imm_addr,
                            [dstaddr_loc, srcaddr_loc, length_loc])

        regalloc.possibly_free_var(length_box)
        regalloc.possibly_free_var(dstaddr_box)
        regalloc.possibly_free_var(srcaddr_box)

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
        self._gen_address(ofsloc, ofs_items, scale, resloc, baseloc)

    def _gen_address(self, sizereg, baseofs, scale, result, baseloc=None):
        assert sizereg.is_reg()
        if scale > 0:
            scaled_loc = r.r0
            if IS_PPC_32:
                self.mc.slwi(scaled_loc.value, sizereg.value, scale)
            else:
                self.mc.sldi(scaled_loc.value, sizereg.value, scale)
        else:
            scaled_loc = sizereg
        if baseloc is not None:
            assert baseloc.is_reg()
            self.mc.add(result.value, baseloc.value, scaled_loc.value)
            self.mc.addi(result.value, result.value, baseofs)
        else:
            self.mc.addi(result.value, scaled_loc.value, baseofs)

    def _get_unicode_item_scale(self):
        _, itemsize, _ = symbolic.get_array_token(rstr.UNICODE,
                                                  self.cpu.translate_support_code)
        if itemsize == 4:
            return 2
        elif itemsize == 2:
            return 1
        else:
            raise AssertionError("bad unicode item size")


class UnicodeOpAssembler(object):

    _mixin_ = True

    emit_unicodelen = StrOpAssembler.emit_strlen

    def emit_unicodegetitem(self, op, arglocs, regalloc):
        # res is used as a temporary location
        # => it is save to use it before loading the result
        res, base_loc, ofs_loc, scale, basesize, itemsize = arglocs

        if IS_PPC_32:
            self.mc.slwi(res.value, ofs_loc.value, scale.value)
        else:
            self.mc.sldi(res.value, ofs_loc.value, scale.value)
        self.mc.add(res.value, base_loc.value, res.value)

        if scale.value == 2:
            self.mc.lwz(res.value, res.value, basesize.value)
        elif scale.value == 1:
            self.mc.lhz(res.value, res.value, basesize.value)
        else:
            assert 0, itemsize.value

    def emit_unicodesetitem(self, op, arglocs, regalloc):
        value_loc, base_loc, ofs_loc, temp_loc, scale, basesize, itemsize = arglocs

        if IS_PPC_32:
            self.mc.slwi(temp_loc.value, ofs_loc.value, scale.value)
        else:
            self.mc.sldi(temp_loc.value, ofs_loc.value, scale.value)
        self.mc.add(temp_loc.value, base_loc.value, temp_loc.value)

        if scale.value == 2:
            self.mc.stw(value_loc.value, temp_loc.value, basesize.value)
        elif scale.value == 1:
            self.mc.sth(value_loc.value, temp_loc.value, basesize.value)
        else:
            assert 0, itemsize.value


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

    def emit_cond_call_gc_wb(self, op, arglocs, regalloc):
        # Write code equivalent to write_barrier() in the GC: it checks
        # a flag in the object at arglocs[0], and if set, it calls the
        # function remember_young_pointer() from the GC.  The two arguments
        # to the call are in arglocs[:2].  The latter saves registers as needed
        # and call the function jit_remember_young_pointer() from the GC.
        descr = op.getdescr()
        if we_are_translated():
            cls = self.cpu.gc_ll_descr.has_write_barrier_class()
            assert cls is not None and isinstance(descr, cls)
        #
        opnum = op.getopnum()
        card_marking = False
        mask = descr.jit_wb_if_flag_singlebyte
        if opnum == rop.COND_CALL_GC_WB_ARRAY and descr.jit_wb_cards_set != 0:
            # assumptions the rest of the function depends on:
            assert (descr.jit_wb_cards_set_byteofs ==
                    descr.jit_wb_if_flag_byteofs)
            assert descr.jit_wb_cards_set_singlebyte == -0x80
            card_marking = True
            mask = descr.jit_wb_if_flag_singlebyte | -0x80
        #
        loc_base = arglocs[0]
        assert _check_imm_arg(descr.jit_wb_if_flag_byteofs)
        with scratch_reg(self.mc):
            self.mc.lbz(r.SCRATCH.value, loc_base.value,
                        descr.jit_wb_if_flag_byteofs)
            # test whether this bit is set
            mask &= 0xFF
            self.mc.andix(r.SCRATCH.value, r.SCRATCH.value, mask)

        jz_location = self.mc.currpos()
        self.mc.nop()

        # for cond_call_gc_wb_array, also add another fast path:
        # if GCFLAG_CARDS_SET, then we can just set one bit and be done
        if card_marking:
            with scratch_reg(self.mc):
                self.mc.lbz(r.SCRATCH.value, loc_base.value,
                            descr.jit_wb_if_flag_byteofs)
                self.mc.extsb(r.SCRATCH.value, r.SCRATCH.value)

                # test whether this bit is set
                self.mc.cmpwi(0, r.SCRATCH.value, 0)

                js_location = self.mc.currpos()
                self.mc.nop()
        else:
            js_location = 0

        # Write only a CALL to the helper prepared in advance, passing it as
        # argument the address of the structure we are writing into
        # (the first argument to COND_CALL_GC_WB).
        helper_num = card_marking

        if self._regalloc.fprm.reg_bindings:
            helper_num += 2
        if self.wb_slowpath[helper_num] == 0:    # tests only
            assert not we_are_translated()
            self.cpu.gc_ll_descr.write_barrier_descr = descr
            self._build_wb_slowpath(card_marking,
                                    bool(self._regalloc.fprm.reg_bindings))
            assert self.wb_slowpath[helper_num] != 0
        #
        if loc_base is not r.r3:
            self.mc.store(r.r3.value, r.SP.value, 24)
            remap_frame_layout(self, [loc_base], [r.r3], r.SCRATCH)
        addr = self.wb_slowpath[helper_num]
        func = rffi.cast(lltype.Signed, addr)
        self.mc.bl_abs(func)
        if loc_base is not r.r3:
            self.mc.load(r.r3.value, r.SP.value, 24)

        # if GCFLAG_CARDS_SET, then we can do the whole thing that would
        # be done in the CALL above with just four instructions, so here
        # is an inline copy of them
        if card_marking:
            with scratch_reg(self.mc):
                jns_location = self.mc.currpos()
                self.mc.nop()  # jump to the exit, patched later
                # patch the JS above
                offset = self.mc.currpos()
                pmc = OverwritingBuilder(self.mc, js_location, 1)
                # Jump if JS comparison is less than (bit set)
                pmc.bc(12, 0, offset - js_location)
                pmc.overwrite()
                #
                # case GCFLAG_CARDS_SET: emit a few instructions to do
                # directly the card flag setting
                loc_index = arglocs[1]
                assert loc_index.is_reg()
                tmp1 = arglocs[-1]
                tmp2 = arglocs[-2]
                tmp3 = arglocs[-3]
                #byteofs
                s = 3 + descr.jit_wb_card_page_shift

                self.mc.srli_op(tmp3.value, loc_index.value, s)
                self.mc.not_(tmp3.value, tmp3.value)

                # byte_index
                self.mc.li(r.SCRATCH.value, 7)
                self.mc.srli_op(loc_index.value, loc_index.value,
                                descr.jit_wb_card_page_shift)
                self.mc.and_(tmp1.value, r.SCRATCH.value, loc_index.value)

                # set the bit
                self.mc.li(tmp2.value, 1)
                self.mc.lbzx(r.SCRATCH.value, loc_base.value, tmp3.value)
                self.mc.sl_op(tmp2.value, tmp2.value, tmp1.value)
                self.mc.or_(r.SCRATCH.value, r.SCRATCH.value, tmp2.value)
                self.mc.stbx(r.SCRATCH.value, loc_base.value, tmp3.value)
                # done

                # patch the JNS above
                offset = self.mc.currpos()
                pmc = OverwritingBuilder(self.mc, jns_location, 1)
                # Jump if JNS comparison is not less than (bit not set)
                pmc.bc(4, 0, offset - jns_location)
                pmc.overwrite()

        # patch the JZ above
        offset = self.mc.currpos()
        pmc = OverwritingBuilder(self.mc, jz_location, 1)
        # Jump if JZ comparison is zero (CMP 0 is equal)
        pmc.bc(12, 2, offset - jz_location)
        pmc.overwrite()

    emit_cond_call_gc_wb_array = emit_cond_call_gc_wb

class ForceOpAssembler(object):

    _mixin_ = True
    
    def emit_force_token(self, op, arglocs, regalloc):
        res_loc = arglocs[0]
        self.mc.mr(res_loc.value, r.SPP.value)
        self.mc.addi(res_loc.value, res_loc.value, FORCE_INDEX_OFS)

    #    self._emit_guard(guard_op, regalloc._prepare_guard(guard_op), c.LT)
    # from: ../x86/assembler.py:1668
    # XXX Split into some helper methods
    def emit_guard_call_assembler(self, op, guard_op, arglocs, regalloc):
        tmploc = arglocs[1]
        resloc = arglocs[2]
        callargs = arglocs[3:]

        faildescr = guard_op.getdescr()
        fail_index = self.cpu.get_fail_descr_number(faildescr)
        self._write_fail_index(fail_index)
        descr = op.getdescr()
        assert isinstance(descr, JitCellToken)
        # check value
        assert tmploc is r.RES
        self._emit_call(fail_index, imm(descr._ppc_func_addr),
                                callargs, result=tmploc)
        if op.result is None:
            value = self.cpu.done_with_this_frame_void_v
        else:
            kind = op.result.type
            if kind == INT:
                value = self.cpu.done_with_this_frame_int_v
            elif kind == REF:
                value = self.cpu.done_with_this_frame_ref_v
            elif kind == FLOAT:
                value = self.cpu.done_with_this_frame_float_v
            else:
                raise AssertionError(kind)

        # take fast path on equality
        # => jump on inequality
        with scratch_reg(self.mc):
            self.mc.load_imm(r.SCRATCH, value)
            self.mc.cmp_op(0, tmploc.value, r.SCRATCH.value)

        #if values are equal we take the fast path
        # Slow path, calling helper
        # jump to merge point

        jd = descr.outermost_jitdriver_sd
        assert jd is not None

        # Path A: load return value and reset token
        # Fast Path using result boxes

        fast_jump_pos = self.mc.currpos()
        self.mc.nop()

        # Reset the vable token --- XXX really too much special logic here:-(
        if jd.index_of_virtualizable >= 0:
            from pypy.jit.backend.llsupport.descr import FieldDescr
            fielddescr = jd.vable_token_descr
            assert isinstance(fielddescr, FieldDescr)
            ofs = fielddescr.offset
            tmploc = regalloc.get_scratch_reg(INT)
            with scratch_reg(self.mc):
                self.mov_loc_loc(arglocs[0], r.SCRATCH)
                self.mc.li(tmploc.value, 0)
                self.mc.storex(tmploc.value, 0, r.SCRATCH.value)

        if op.result is not None:
            # load the return value from fail_boxes_xxx[0]
            kind = op.result.type
            if kind == INT:
                adr = self.fail_boxes_int.get_addr_for_num(0)
            elif kind == REF:
                adr = self.fail_boxes_ptr.get_addr_for_num(0)
            elif kind == FLOAT:
                adr = self.fail_boxes_float.get_addr_for_num(0)
            else:
                raise AssertionError(kind)
            with scratch_reg(self.mc):
                self.mc.load_imm(r.SCRATCH, adr)
                if op.result.type == FLOAT:
                    self.mc.lfdx(resloc.value, 0, r.SCRATCH.value)
                else:
                    self.mc.loadx(resloc.value, 0, r.SCRATCH.value)

        # jump to merge point, patched later
        fast_path_to_end_jump_pos = self.mc.currpos()
        self.mc.nop()

        jmp_pos = self.mc.currpos()
        pmc = OverwritingBuilder(self.mc, fast_jump_pos, 1)
        pmc.bc(4, 2, jmp_pos - fast_jump_pos)
        pmc.overwrite()

        # Path B: use assembler helper
        asm_helper_adr = self.cpu.cast_adr_to_int(jd.assembler_helper_adr)
        if self.cpu.supports_floats:
            floats = r.VOLATILES_FLOAT
        else:
            floats = []

        with Saved_Volatiles(self.mc, save_RES=False):
            # result of previous call is in r3
            self.mov_loc_loc(arglocs[0], r.r4)
            self.mc.call(asm_helper_adr)

        # merge point
        currpos = self.mc.currpos()
        pmc = OverwritingBuilder(self.mc, fast_path_to_end_jump_pos, 1)
        pmc.b(currpos - fast_path_to_end_jump_pos)
        pmc.overwrite()

        with scratch_reg(self.mc):
            self.mc.load(r.SCRATCH.value, r.SPP.value, FORCE_INDEX_OFS)
            self.mc.cmp_op(0, r.SCRATCH.value, 0, imm=True)

        self._emit_guard(guard_op, regalloc._prepare_guard(guard_op),
                                                    c.LT, save_exc=True)

    # ../x86/assembler.py:668
    def redirect_call_assembler(self, oldlooptoken, newlooptoken):
        # some minimal sanity checking
        old_nbargs = oldlooptoken.compiled_loop_token._debug_nbargs
        new_nbargs = newlooptoken.compiled_loop_token._debug_nbargs
        assert old_nbargs == new_nbargs
        oldadr = oldlooptoken._ppc_func_addr
        target = newlooptoken._ppc_func_addr
        if IS_PPC_32:
            # we overwrite the instructions at the old _ppc_func_addr
            # to start with a JMP to the new _ppc_func_addr.
            # Ideally we should rather patch all existing CALLs, but well.
            mc = PPCBuilder()
            mc.b_abs(target)
            mc.copy_to_raw_memory(oldadr)
        else:
            # PPC64 trampolines are data so overwrite the code address
            # in the function descriptor at the old address
            # (TOC and static chain pointer are the same).
            odata = rffi.cast(rffi.CArrayPtr(lltype.Signed), oldadr)
            tdata = rffi.cast(rffi.CArrayPtr(lltype.Signed), target)
            odata[0] = tdata[0]

    def emit_guard_call_may_force(self, op, guard_op, arglocs, regalloc):
        faildescr = guard_op.getdescr()
        fail_index = self.cpu.get_fail_descr_number(faildescr)
        self._write_fail_index(fail_index)
        numargs = op.numargs()
        callargs = arglocs[2:numargs + 1]  # extract the arguments to the call
        adr = arglocs[1]
        resloc = arglocs[0]
        #
        descr = op.getdescr()
        size = descr.get_result_size()
        signed = descr.is_result_signed()
        #
        self._emit_call(fail_index, adr, callargs, resloc, (size, signed))

        with scratch_reg(self.mc):
            self.mc.load(r.SCRATCH.value, r.SPP.value, FORCE_INDEX_OFS)
            self.mc.cmp_op(0, r.SCRATCH.value, 0, imm=True)

        self._emit_guard(guard_op, arglocs[1 + numargs:], c.LT, save_exc=True)

    def emit_guard_call_release_gil(self, op, guard_op, arglocs, regalloc):

        # first, close the stack in the sense of the asmgcc GC root tracker
        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        numargs = op.numargs()
        callargs = arglocs[2:numargs + 1]  # extract the arguments to the call
        adr = arglocs[1]
        resloc = arglocs[0]

        if gcrootmap:
            self.call_release_gil(gcrootmap, arglocs)
        # do the call
        faildescr = guard_op.getdescr()
        fail_index = self.cpu.get_fail_descr_number(faildescr)
        self._write_fail_index(fail_index)
        #
        descr = op.getdescr()
        size = descr.get_result_size()
        signed = descr.is_result_signed()
        #
        self._emit_call(fail_index, adr, callargs, resloc, (size, signed))
        # then reopen the stack
        if gcrootmap:
            self.call_reacquire_gil(gcrootmap, resloc)

        with scratch_reg(self.mc):
            self.mc.load(r.SCRATCH.value, r.SPP.value, 0)
            self.mc.cmp_op(0, r.SCRATCH.value, 0, imm=True)

        self._emit_guard(guard_op, arglocs[1 + numargs:], c.LT, save_exc=True)

    def call_release_gil(self, gcrootmap, save_registers):
        # XXX don't know whether this is correct
        # XXX use save_registers here
        assert gcrootmap.is_shadow_stack
        with Saved_Volatiles(self.mc):
            #self._emit_call(NO_FORCE_INDEX, self.releasegil_addr, 
            #                [], self._regalloc)
            self._emit_call(NO_FORCE_INDEX, imm(self.releasegil_addr), [])

    def call_reacquire_gil(self, gcrootmap, save_loc):
        # save the previous result into the stack temporarily.
        # XXX like with call_release_gil(), we assume that we don't need
        # to save vfp regs in this case. Besides the result location
        assert gcrootmap.is_shadow_stack
        with Saved_Volatiles(self.mc):
            self._emit_call(NO_FORCE_INDEX, imm(self.reacqgil_addr), [])


class OpAssembler(IntOpAssembler, GuardOpAssembler,
                  MiscOpAssembler, FieldOpAssembler,
                  ArrayOpAssembler, StrOpAssembler,
                  UnicodeOpAssembler, ForceOpAssembler,
                  AllocOpAssembler, FloatOpAssembler):

    def nop(self):
        self.mc.ori(0, 0, 0)

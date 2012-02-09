from pypy.jit.backend.ppc.helper.assembler import (gen_emit_cmp_op, 
                                                          gen_emit_unary_cmp_op)
import pypy.jit.backend.ppc.condition as c
import pypy.jit.backend.ppc.register as r
from pypy.jit.backend.ppc.arch import (IS_PPC_32, WORD,
                                              GPR_SAVE_AREA, BACKCHAIN_SIZE,
                                              MAX_REG_PARAMS)

from pypy.jit.metainterp.history import (JitCellToken, TargetToken, Box,
                                         AbstractFailDescr, FLOAT, INT, REF)
from pypy.rlib.objectmodel import we_are_translated
from pypy.jit.backend.ppc.helper.assembler import (count_reg_args,
                                                          Saved_Volatiles)
from pypy.jit.backend.ppc.jump import remap_frame_layout
from pypy.jit.backend.ppc.codebuilder import OverwritingBuilder
from pypy.jit.backend.ppc.regalloc import TempPtr, TempInt
from pypy.jit.backend.llsupport import symbolic
from pypy.rpython.lltypesystem import rstr, rffi, lltype
from pypy.jit.metainterp.resoperation import rop

NO_FORCE_INDEX = -1

class GuardToken(object):
    def __init__(self, descr, failargs, faillocs, offset, fcond=c.NE,
                                        save_exc=False, is_invalidate=False):
        self.descr = descr
        self.offset = offset
        self.is_invalidate = is_invalidate
        self.failargs = failargs
        self.faillocs = faillocs
        self.save_exc = save_exc
        self.fcond=fcond

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
            self.mc.load_imm(r.r0, l0.value)
            self.mc.sub(res.value, r.r0.value, l1.value)
        elif l1.is_imm():
            self.mc.subi(res.value, l0.value, l1.value)
        else:
            self.mc.sub(res.value, l0.value, l1.value)
 
    def emit_int_sub_ovf(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        self.mc.subfo(res.value, l1.value, l0.value)

    def emit_int_mul(self, op, arglocs, regalloc):
        reg1, reg2, res = arglocs
        if IS_PPC_32:
            self.mc.mullw(res.value, reg1.value, reg2.value)
        else:
            self.mc.mulld(res.value, reg1.value, reg2.value)

    def emit_int_mul_ovf(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        if IS_PPC_32:
            self.mc.mullwo(res.value, l0.value, l1.value)
        else:
            self.mc.mulldo(res.value, l0.value, l1.value)

    def emit_int_floordiv(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        if IS_PPC_32:
            div = self.mc.divw
        else:
            div = self.mc.divd

        if l0.is_imm():
            self.mc.load_imm(r.r0, l0.value)
            div(res.value, r.r0.value, l1.value)
        elif l1.is_imm():
            self.mc.load_imm(r.r0, l1.value)
            div(res.value, l0.value, r.r0.value)
        else:
            div(res.value, l0.value, l1.value)

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


class GuardOpAssembler(object):

    _mixin_ = True

    def _emit_guard(self, op, arglocs, fcond, save_exc=False,
            is_guard_not_invalidated=False):
        descr = op.getdescr()
        assert isinstance(descr, AbstractFailDescr)
        pos = self.mc.currpos()
        self.mc.nop()     # has to be patched later on
        self.pending_guards.append(GuardToken(descr,
                                   failargs=op.getfailargs(),
                                   faillocs=arglocs,
                                   offset=pos,
                                   fcond=fcond,
                                   is_invalidate=is_guard_not_invalidated,
                                   save_exc=save_exc))

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
        self.mc.alloc_scratch_reg()
        self.mc.mfspr(r.SCRATCH.value, 1)
        # shift and mask to get comparison result
        self.mc.rlwinm(r.SCRATCH.value, r.SCRATCH.value, 1, 0, 0)
        self.mc.cmp_op(0, r.SCRATCH.value, 0, imm=True)
        self.mc.free_scratch_reg()
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
        else:
            assert 0, "not implemented yet"
        self._emit_guard(op, failargs, c.NE)

    emit_guard_nonnull = emit_guard_true
    emit_guard_isnull = emit_guard_false

    def _cmp_guard_class(self, op, locs, regalloc):
        offset = locs[2]
        if offset is not None:
            self.mc.alloc_scratch_reg()
            if offset.is_imm():
                self.mc.load(r.SCRATCH.value, locs[0].value, offset.value)
            else:
                assert offset.is_reg()
                self.mc.loadx(r.SCRATCH.value, locs[0].value, offset.value)
            self.mc.cmp_op(0, r.SCRATCH.value, locs[1].value)
            self.mc.free_scratch_reg()
        else:
            assert 0, "not implemented yet"
        self._emit_guard(op, locs[3:], c.NE)

    def emit_guard_class(self, op, arglocs, regalloc):
        self._cmp_guard_class(op, arglocs, regalloc)

    def emit_guard_nonnull_class(self, op, arglocs, regalloc):
        offset = self.cpu.vtable_offset
        self.mc.cmp_op(0, arglocs[0].value, 0, imm=True)
        if offset is not None:
            self._emit_guard(op, arglocs[3:], c.EQ)
        else:
            raise NotImplementedError
        self._cmp_guard_class(op, arglocs, regalloc)

    def emit_guard_not_invalidated(self, op, locs, regalloc):
        return self._emit_guard(op, locs, c.EQ, is_guard_not_invalidated=True)

class MiscOpAssembler(object):

    _mixin_ = True

    def emit_finish(self, op, arglocs, regalloc):
        for i in range(len(arglocs) - 1):
            loc = arglocs[i]
            box = op.getarg(i)
            if loc is None:
                continue
            if loc.is_reg():
                if box.type == REF:
                    adr = self.fail_boxes_ptr.get_addr_for_num(i)
                elif box.type == INT:
                    adr = self.fail_boxes_int.get_addr_for_num(i)
                else:
                    assert 0
                self.mc.alloc_scratch_reg()
                self.mc.load_imm(r.SCRATCH, adr)
                self.mc.storex(loc.value, 0, r.SCRATCH.value)
                self.mc.free_scratch_reg()
            elif loc.is_vfp_reg():
                assert box.type == FLOAT
                assert 0, "not implemented yet"
            elif loc.is_stack() or loc.is_imm() or loc.is_imm_float():
                if box.type == FLOAT:
                    assert 0, "not implemented yet"
                elif box.type == REF or box.type == INT:
                    if box.type == REF:
                        adr = self.fail_boxes_ptr.get_addr_for_num(i)
                    elif box.type == INT:
                        adr = self.fail_boxes_int.get_addr_for_num(i)
                    else:
                        assert 0
                    self.mc.alloc_scratch_reg()
                    self.mov_loc_loc(loc, r.SCRATCH)
                    # store content of r5 temporary in ENCODING AREA
                    self.mc.store(r.r5.value, r.SPP.value, 0)
                    self.mc.load_imm(r.r5, adr)
                    self.mc.store(r.SCRATCH.value, r.r5.value, 0)
                    self.mc.free_scratch_reg()
                    # restore r5
                    self.mc.load(r.r5.value, r.SPP.value, 0)
            else:
                assert 0
        # note: no exception should currently be set in llop.get_exception_addr
        # even if this finish may be an exit_frame_with_exception (in this case
        # the exception instance is in arglocs[0]).
        addr = self.cpu.get_on_leave_jitted_int(save_exception=False)
        self.mc.call(addr)
        self.mc.load_imm(r.RES, arglocs[-1].value)
        self._gen_epilogue(self.mc)

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

        self.mc.alloc_scratch_reg()
        self.mc.load(r.SCRATCH.value, loc1.value, 0)
        self.mc.cmp_op(0, r.SCRATCH.value, loc.value)
        self.mc.free_scratch_reg()

        self._emit_guard(op, failargs, c.NE, save_exc=True)
        self.mc.load_imm(loc, pos_exc_value.value)

        if resloc:
            self.mc.load(resloc.value, loc.value, 0)

        self.mc.alloc_scratch_reg()
        self.mc.load_imm(r.SCRATCH, 0)
        self.mc.store(r.SCRATCH.value, loc.value, 0)
        self.mc.store(r.SCRATCH.value, loc1.value, 0)
        self.mc.free_scratch_reg()

    def emit_call(self, op, args, regalloc, force_index=-1):
        adr = args[0].value
        arglist = op.getarglist()[1:]
        if force_index == -1:
            force_index = self.write_new_force_index()
        self._emit_call(force_index, adr, arglist, regalloc, op.result)
        descr = op.getdescr()
        #XXX Hack, Hack, Hack
        if op.result and not we_are_translated():
            #XXX check result type
            loc = regalloc.rm.call_result_location(op.result)
            size = descr.get_result_size()
            signed = descr.is_result_signed()
            self._ensure_result_bit_extension(loc, size, signed)

    def _emit_call(self, force_index, adr, args, regalloc, result=None):
        n_args = len(args)
        reg_args = count_reg_args(args)

        n = 0   # used to count the number of words pushed on the stack, so we
                # can later modify the SP back to its original value
        stack_args = []
        if n_args > reg_args:
            # first we need to prepare the list so it stays aligned
            count = 0
            for i in range(reg_args, n_args):
                arg = args[i]
                if arg.type == FLOAT:
                    assert 0, "not implemented yet"
                else:
                    count += 1
                    n += WORD
                stack_args.append(arg)
            if count % 2 != 0:
                n += WORD
                stack_args.append(None)

        # compute maximum of parameters passed
        self.max_stack_params = max(self.max_stack_params, len(stack_args))

        # compute offset at which parameters are stored
        if IS_PPC_32:
            param_offset = BACKCHAIN_SIZE * WORD
        else:
            param_offset = ((BACKCHAIN_SIZE + MAX_REG_PARAMS)
                    * WORD) # space for first 8 parameters

        self.mc.alloc_scratch_reg()
        for i, arg in enumerate(stack_args):
            offset = param_offset + i * WORD
            if arg is not None:
                self.regalloc_mov(regalloc.loc(arg), r.SCRATCH)
            self.mc.store(r.SCRATCH.value, r.SP.value, offset)
        self.mc.free_scratch_reg()

        # collect variables that need to go in registers
        # and the registers they will be stored in 
        num = 0
        count = 0
        non_float_locs = []
        non_float_regs = []
        for i in range(reg_args):
            arg = args[i]
            if arg.type == FLOAT and count % 2 != 0:
                assert 0, "not implemented yet"
            reg = r.PARAM_REGS[num]

            if arg.type == FLOAT:
                assert 0, "not implemented yet"
            else:
                non_float_locs.append(regalloc.loc(arg))
                non_float_regs.append(reg)

            if arg.type == FLOAT:
                assert 0, "not implemented yet"
            else:
                num += 1
                count += 1

        # spill variables that need to be saved around calls
        regalloc.before_call(save_all_regs=2)

        # remap values stored in core registers
        remap_frame_layout(self, non_float_locs, non_float_regs, r.SCRATCH)

        # the actual call
        self.mc.call(adr)

        self.mark_gc_roots(force_index)

        # restore the arguments stored on the stack
        if result is not None:
            resloc = regalloc.after_call(result)


class FieldOpAssembler(object):

    _mixin_ = True

    def emit_setfield_gc(self, op, arglocs, regalloc):
        value_loc, base_loc, ofs, size = arglocs
        if size.value == 8:
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

        #XXX Hack, Hack, Hack
        if not we_are_translated():
            signed = op.getdescr().is_field_signed()
            self._ensure_result_bit_extension(res, size.value, signed)

    emit_getfield_raw = emit_getfield_gc
    emit_getfield_raw_pure = emit_getfield_gc
    emit_getfield_gc_pure = emit_getfield_gc

    def emit_getinteriorfield_gc(self, op, arglocs, regalloc):
        (base_loc, index_loc, res_loc,
            ofs_loc, ofs, itemsize, fieldsize) = arglocs
        self.mc.load_imm(r.SCRATCH, itemsize.value)
        self.mc.mullw(r.SCRATCH.value, index_loc.value, r.SCRATCH.value)
        if ofs.value > 0:
            if ofs_loc.is_imm():
                self.mc.addic(r.SCRATCH.value, r.SCRATCH.value, ofs_loc.value)
            else:
                self.mc.add(r.SCRATCH.value, r.SCRATCH.value, ofs_loc.value)

        if fieldsize.value == 8:
            self.mc.ldx(res_loc.value, base_loc.value, r.SCRATCH.value)
        elif fieldsize.value == 4:
            self.mc.lwzx(res_loc.value, base_loc.value, r.SCRATCH.value)
        elif fieldsize.value == 2:
            self.mc.lhzx(res_loc.value, base_loc.value, r.SCRATCH.value)
        elif fieldsize.value == 1:
            self.mc.lbzx(res_loc.value, base_loc.value, r.SCRATCH.value)
        else:
            assert 0

        #XXX Hack, Hack, Hack
        if not we_are_translated():
            signed = op.getdescr().fielddescr.is_field_signed()
            self._ensure_result_bit_extension(res_loc, fieldsize.value, signed)

    def emit_setinteriorfield_gc(self, op, arglocs, regalloc):
        (base_loc, index_loc, value_loc,
            ofs_loc, ofs, itemsize, fieldsize) = arglocs
        self.mc.load_imm(r.SCRATCH, itemsize.value)
        self.mc.mullw(r.SCRATCH.value, index_loc.value, r.SCRATCH.value)
        if ofs.value > 0:
            if ofs_loc.is_imm():
                self.mc.addic(r.SCRATCH.value, r.SCRATCH.value, ofs_loc.value)
            else:
                self.mc.add(r.SCRATCH.value, r.SCRATCH.value, ofs_loc.value)
        if fieldsize.value == 8:
            self.mc.stdx(value_loc.value, base_loc.value, r.SCRATCH.value)
        elif fieldsize.value == 4:
            self.mc.stwx(value_loc.value, base_loc.value, r.SCRATCH.value)
        elif fieldsize.value == 2:
            self.mc.sthx(value_loc.value, base_loc.value, r.SCRATCH.value)
        elif fieldsize.value == 1:
            self.mc.stbx(value_loc.value, base_loc.value, r.SCRATCH.value)
        else:
            assert 0


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

    def emit_getarrayitem_gc(self, op, arglocs, regalloc):
        res, base_loc, ofs_loc, scratch_loc, scale, ofs = arglocs
        assert ofs_loc.is_reg()

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
            self.mc.ldx(res.value, base_loc.value, scale_loc.value)
        elif scale.value == 2:
            self.mc.lwzx(res.value, base_loc.value, scale_loc.value)
        elif scale.value == 1:
            self.mc.lhzx(res.value, base_loc.value, scale_loc.value)
        elif scale.value == 0:
            self.mc.lbzx(res.value, base_loc.value, scale_loc.value)
        else:
            assert 0

        #XXX Hack, Hack, Hack
        if not we_are_translated():
            descr = op.getdescr()
            size =  descr.itemsize
            signed = descr.is_item_signed()
            self._ensure_result_bit_extension(res, size, signed)

    emit_getarrayitem_raw = emit_getarrayitem_gc
    emit_getarrayitem_gc_pure = emit_getarrayitem_gc


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
        value_loc, base_loc, ofs_loc, basesize = arglocs
        if ofs_loc.is_imm():
            self.mc.addi(base_loc.value, base_loc.value, ofs_loc.getint())
        else:
            self.mc.add(base_loc.value, base_loc.value, ofs_loc.value)
        self.mc.stb(value_loc.value, base_loc.value, basesize.value)

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
            self.mc.alloc_scratch_reg()
            self.mc.load_imm(r.SCRATCH, 1 << scale)
            if IS_PPC_32:
                self.mc.mullw(bytes_loc.value, r.SCRATCH.value, length_loc.value)
            else:
                self.mc.mulld(bytes_loc.value, r.SCRATCH.value, length_loc.value)
            self.mc.free_scratch_reg()
            length_box = bytes_box
            length_loc = bytes_loc
        # call memcpy()
        self._emit_call(NO_FORCE_INDEX, self.memcpy_addr, 
                [dstaddr_box, srcaddr_box, length_box], regalloc)

        regalloc.possibly_free_var(length_box)
        regalloc.possibly_free_var(dstaddr_box)
        regalloc.possibly_free_var(srcaddr_box)

    def _gen_address_inside_string(self, baseloc, ofsloc, resloc, is_unicode):
        cpu = self.cpu
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

    # XXX 64 bit adjustment
    def emit_unicodegetitem(self, op, arglocs, regalloc):
        res, base_loc, ofs_loc, scale, basesize, itemsize = arglocs

        if IS_PPC_32:
            self.mc.slwi(ofs_loc.value, ofs_loc.value, scale.value)
        else:
            self.mc.sldi(ofs_loc.value, ofs_loc.value, scale.value)
        self.mc.add(res.value, base_loc.value, ofs_loc.value)

        if scale.value == 2:
            self.mc.lwz(res.value, res.value, basesize.value)
        elif scale.value == 1:
            self.mc.lhz(res.value, res.value, basesize.value)
        else:
            assert 0, itemsize.value

    # XXX 64 bit adjustment
    def emit_unicodesetitem(self, op, arglocs, regalloc):
        value_loc, base_loc, ofs_loc, scale, basesize, itemsize = arglocs

        if IS_PPC_32:
            self.mc.slwi(ofs_loc.value, ofs_loc.value, scale.value)
        else:
            self.mc.sldi(ofs_loc.value, ofs_loc.value, scale.value)
        self.mc.add(base_loc.value, base_loc.value, ofs_loc.value)

        if scale.value == 2:
            self.mc.stw(value_loc.value, base_loc.value, basesize.value)
        elif scale.value == 1:
            self.mc.sth(value_loc.value, base_loc.value, basesize.value)
        else:
            assert 0, itemsize.value


class AllocOpAssembler(object):

    _mixin_ = True

    def emit_call_malloc_gc(self, op, arglocs, regalloc):
        self.emit_call(op, arglocs, regalloc)
        self.propagate_memoryerror_if_r3_is_null()

    def set_vtable(self, box, vtable):
        if self.cpu.vtable_offset is not None:
            adr = rffi.cast(lltype.Signed, vtable)
            self.mc.alloc_scratch_reg()
            self.mc.load_imm(r.SCRATCH, adr)
            self.mc.store(r.SCRATCH.value, r.RES.value, self.cpu.vtable_offset)
            self.mc.free_scratch_reg()

    def write_new_force_index(self):
        # for shadowstack only: get a new, unused force_index number and
        # write it to FORCE_INDEX_OFS.  Used to record the call shape
        # (i.e. where the GC pointers are in the stack) around a CALL
        # instruction that doesn't already have a force_index.
        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap and gcrootmap.is_shadow_stack:
            clt = self.current_clt
            force_index = clt.reserve_and_record_some_faildescr_index()
            self._write_fail_index(force_index)
            return force_index
        else:
            return 0

    def emit_debug_merge_point(self, op, arglocs, regalloc):
        pass

    emit_jit_debug = emit_debug_merge_point

    def emit_cond_call_gc_wb(self, op, arglocs, regalloc):
        # Write code equivalent to write_barrier() in the GC: it checks
        # a flag in the object at arglocs[0], and if set, it calls the
        # function remember_young_pointer() from the GC.  The two arguments
        # to the call are in arglocs[:2].  The rest, arglocs[2:], contains
        # registers that need to be saved and restored across the call.
        descr = op.getdescr()
        if we_are_translated():
            cls = self.cpu.gc_ll_descr.has_write_barrier_class()
            assert cls is not None and isinstance(descr, cls)

        opnum = op.getopnum()
        if opnum == rop.COND_CALL_GC_WB:
            N = 2
            addr = descr.get_write_barrier_fn(self.cpu)
        elif opnum == rop.COND_CALL_GC_WB_ARRAY:
            N = 3
            addr = descr.get_write_barrier_from_array_fn(self.cpu)
            assert addr != 0
        else:
            raise AssertionError(opnum)
        loc_base = arglocs[0]

        self.mc.alloc_scratch_reg()
        self.mc.load(r.SCRATCH.value, loc_base.value, 0)

        # get the position of the bit we want to test
        bitpos = descr.jit_wb_if_flag_bitpos

        if IS_PPC_32:
            # put this bit to the rightmost bitposition of r0
            if bitpos > 0:
                self.mc.rlwinm(r.SCRATCH.value, r.SCRATCH.value,
                               32 - bitpos, 31, 31)
            # test whether this bit is set
            self.mc.cmpwi(0, r.SCRATCH.value, 1)
        else:
            if bitpos > 0:
                self.mc.rldicl(r.SCRATCH.value, r.SCRATCH.value,
                               64 - bitpos, 63)
            # test whether this bit is set
            self.mc.cmpdi(0, r.SCRATCH.value, 1)
        self.mc.free_scratch_reg()

        jz_location = self.mc.currpos()
        self.mc.nop()

        # the following is supposed to be the slow path, so whenever possible
        # we choose the most compact encoding over the most efficient one.
        with Saved_Volatiles(self.mc):
            if N == 2:
                callargs = [r.r3, r.r4]
            else:
                callargs = [r.r3, r.r4, r.r5]
            remap_frame_layout(self, arglocs, callargs, r.SCRATCH)
            func = rffi.cast(lltype.Signed, addr)
            #
            # misaligned stack in the call, but it's ok because the write barrier
            # is not going to call anything more.  
            self.mc.call(func)

        # patch the JZ above
        offset = self.mc.currpos() - jz_location
        pmc = OverwritingBuilder(self.mc, jz_location, 1)
        pmc.bc(4, 2, offset) # jump if the two values are equal
        pmc.overwrite()

    emit_cond_call_gc_wb_array = emit_cond_call_gc_wb

class ForceOpAssembler(object):

    _mixin_ = True
    
    def emit_force_token(self, op, arglocs, regalloc):
        res_loc = arglocs[0]
        self.mc.mr(res_loc.value, r.SPP.value)

    # from: ../x86/assembler.py:1668
    # XXX Split into some helper methods
    def emit_guard_call_assembler(self, op, guard_op, arglocs, regalloc):
        faildescr = guard_op.getdescr()
        fail_index = self.cpu.get_fail_descr_number(faildescr)
        self._write_fail_index(fail_index)

        descr = op.getdescr()
        assert isinstance(descr, JitCellToken)
        # XXX check this
        #assert op.numargs() == len(descr._ppc_arglocs[0])
        resbox = TempInt()
        self._emit_call(fail_index, descr._ppc_func_addr, op.getarglist(),
                                regalloc, result=resbox)
        if op.result is None:
            value = self.cpu.done_with_this_frame_void_v
        else:
            kind = op.result.type
            if kind == INT:
                value = self.cpu.done_with_this_frame_int_v
            elif kind == REF:
                value = self.cpu.done_with_this_frame_ref_v
            elif kind == FLOAT:
                assert 0, "not implemented yet"
            else:
                raise AssertionError(kind)
        # check value
        resloc = regalloc.try_allocate_reg(resbox)
        assert resloc is r.RES
        self.mc.alloc_scratch_reg()
        self.mc.load_imm(r.SCRATCH, value)
        self.mc.cmp_op(0, resloc.value, r.SCRATCH.value)
        self.mc.free_scratch_reg()
        regalloc.possibly_free_var(resbox)

        fast_jmp_pos = self.mc.currpos()
        self.mc.nop()

        # Path A: use assembler helper
        # if values are equal we take the fast path
        # Slow path, calling helper
        # jump to merge point
        jd = descr.outermost_jitdriver_sd
        assert jd is not None
        asm_helper_adr = self.cpu.cast_adr_to_int(jd.assembler_helper_adr)

        # do call to helper function
        self.mov_loc_loc(arglocs[1], r.r4)
        self.mc.call(asm_helper_adr)

        if op.result:
            resloc = regalloc.after_call(op.result)
            if resloc.is_vfp_reg():
                assert 0, "not implemented yet"

        # jump to merge point
        jmp_pos = self.mc.currpos()
        self.mc.nop()

        # Path B: load return value and reset token
        # Fast Path using result boxes
        # patch the jump to the fast path
        offset = self.mc.currpos() - fast_jmp_pos
        pmc = OverwritingBuilder(self.mc, fast_jmp_pos, 1)
        # 12 and 2 mean: jump if the 3rd bit in CR is set
        pmc.bc(12, 2, offset)
        pmc.overwrite()

        # Reset the vable token --- XXX really too much special logic here:-(
        if jd.index_of_virtualizable >= 0:
            from pypy.jit.backend.llsupport.descr import FieldDescr
            fielddescr = jd.vable_token_descr
            assert isinstance(fielddescr, FieldDescr)
            ofs = fielddescr.offset
            resloc = regalloc.force_allocate_reg(resbox)
            self.mc.alloc_scratch_reg()
            self.mov_loc_loc(arglocs[1], r.SCRATCH)
            self.mc.li(resloc.value, 0)
            self.mc.storex(resloc.value, 0, r.SCRATCH.value)
            self.mc.free_scratch_reg()
            regalloc.possibly_free_var(resbox)

        if op.result is not None:
            # load the return value from fail_boxes_xxx[0]
            kind = op.result.type
            if kind == INT:
                adr = self.fail_boxes_int.get_addr_for_num(0)
            elif kind == REF:
                adr = self.fail_boxes_ptr.get_addr_for_num(0)
            elif kind == FLOAT:
                assert 0, "not implemented yet"
            else:
                raise AssertionError(kind)
            resloc = regalloc.force_allocate_reg(op.result)
            regalloc.possibly_free_var(resbox)
            self.mc.alloc_scratch_reg()
            self.mc.load_imm(r.SCRATCH, adr)
            if op.result.type == FLOAT:
                assert 0, "not implemented yet"
            else:
                self.mc.loadx(resloc.value, 0, r.SCRATCH.value)
            self.mc.free_scratch_reg()

        # merge point
        offset = self.mc.currpos() - jmp_pos
        if offset >= 0:
            pmc = OverwritingBuilder(self.mc, jmp_pos, 1)
            pmc.b(offset)
            pmc.overwrite()

        self.mc.alloc_scratch_reg()
        self.mc.load(r.SCRATCH.value, r.SPP.value, 0)
        self.mc.cmp_op(0, r.SCRATCH.value, 0, imm=True)
        self.mc.free_scratch_reg()

        self._emit_guard(guard_op, regalloc._prepare_guard(guard_op), c.LT)

    # ../x86/assembler.py:668
    def redirect_call_assembler(self, oldlooptoken, newlooptoken):
        # some minimal sanity checking
        old_nbargs = oldlooptoken.compiled_loop_token._debug_nbargs
        new_nbargs = newlooptoken.compiled_loop_token._debug_nbargs
        assert old_nbargs == new_nbargs
        # we overwrite the instructions at the old _ppc_func_addr
        # to start with a JMP to the new _ppc_func_addr.
        # Ideally we should rather patch all existing CALLs, but well.
        oldadr = oldlooptoken._ppc_func_addr
        target = newlooptoken._ppc_func_addr
        mc = PPCBuilder()
        mc.b_abs(target)
        mc.copy_to_raw_memory(oldadr)

    def emit_guard_call_may_force(self, op, guard_op, arglocs, regalloc):
        ENCODING_AREA = len(r.MANAGED_REGS) * WORD
        self.mc.alloc_scratch_reg()
        self.mc.load(r.SCRATCH.value, r.SPP.value, ENCODING_AREA)
        self.mc.cmp_op(0, r.SCRATCH.value, 0, imm=True)
        self.mc.free_scratch_reg()
        self._emit_guard(guard_op, arglocs, c.LT)

    emit_guard_call_release_gil = emit_guard_call_may_force

    def call_release_gil(self, gcrootmap, save_registers):
        # XXX don't know whether this is correct
        # XXX use save_registers here
        assert gcrootmap.is_shadow_stack
        with Saved_Volatiles(self.mc):
            self._emit_call(NO_FORCE_INDEX, self.releasegil_addr, 
                            [], self._regalloc)



class OpAssembler(IntOpAssembler, GuardOpAssembler,
                  MiscOpAssembler, FieldOpAssembler,
                  ArrayOpAssembler, StrOpAssembler,
                  UnicodeOpAssembler, ForceOpAssembler,
                  AllocOpAssembler):

    def nop(self):
        self.mc.ori(0, 0, 0)

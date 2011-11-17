from pypy.jit.backend.ppc.ppcgen.helper.assembler import (gen_emit_cmp_op, 
                                                          gen_emit_unary_cmp_op)
import pypy.jit.backend.ppc.ppcgen.condition as c
import pypy.jit.backend.ppc.ppcgen.register as r
from pypy.jit.backend.ppc.ppcgen.arch import (IS_PPC_32, WORD,
                                              GPR_SAVE_AREA, BACKCHAIN_SIZE,
                                              MAX_REG_PARAMS)

from pypy.jit.metainterp.history import LoopToken, AbstractFailDescr, FLOAT
from pypy.rlib.objectmodel import we_are_translated
from pypy.jit.backend.ppc.ppcgen.helper.assembler import count_reg_args 
from pypy.jit.backend.ppc.ppcgen.jump import remap_frame_layout
from pypy.jit.backend.ppc.ppcgen.regalloc import TempPtr
from pypy.jit.backend.llsupport import symbolic
from pypy.rpython.lltypesystem import rstr, rffi, lltype

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

#class OpAssembler(object):
class IntOpAssembler(object):
        
    _mixin_ = True

    # ********************************************************
    # *               I N T    O P E R A T I O N S           *
    # ********************************************************

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
        if IS_PPC_32:
            self.mc.cmpwi(l0.value, 0)
        else:
            self.mc.cmpdi(l0.value, 0)
        self._emit_guard(op, failargs, c.EQ)
        #                        #      ^^^^ If this condition is met,
        #                        #           then the guard fails.

    def emit_guard_false(self, op, arglocs, regalloc):
            l0 = arglocs[0]
            failargs = arglocs[1:]
            if IS_PPC_32:
                self.mc.cmpwi(l0.value, 0)
            else:
                self.mc.cmpdi(l0.value, 0)
            self._emit_guard(op, failargs, c.NE)

    # TODO - Evaluate whether this can be done with 
    #        SO bit instead of OV bit => usage of CR
    #        instead of XER could be more efficient
    def _emit_ovf_guard(self, op, arglocs, cond):
        # move content of XER to GPR
        self.mc.mfspr(r.r0.value, 1)
        # shift and mask to get comparison result
        self.mc.rlwinm(r.r0.value, r.r0.value, 1, 0, 0)
        if IS_PPC_32:
            self.mc.cmpwi(r.r0.value, 0)
        else:
            self.mc.cmpdi(r.r0.value, 0)
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
                if IS_PPC_32:
                    self.mc.cmpwi(l0.value, l1.getint())
                else:
                    self.mc.cmpdi(l0.value, l1.getint())
            else:
                if IS_PPC_32:
                    self.mc.cmpw(l0.value, l1.value)
                else:
                    self.mc.cmpd(l0.value, l1.value)
        else:
            assert 0, "not implemented yet"
        self._emit_guard(op, failargs, c.NE)

    emit_guard_nonnull = emit_guard_true
    emit_guard_isnull = emit_guard_false

    def _cmp_guard_class(self, op, locs, regalloc):
        offset = locs[2]
        if offset is not None:
            if offset.is_imm():
                if IS_PPC_32:
                    self.mc.lwz(r.r0.value, locs[0].value, offset.value)
                else:
                    self.mc.ld(r.r0.value, locs[0].value, offset.value)
            else:
                if IS_PPC_32:
                    self.mc.lwzx(r.r0.value, locs[0].value, offset.value)
                else:
                    self.mc.ldx(r.r0.value, locs[0].value, offset.value)
            self.mc.cmp(r.r0.value, locs[1].value)
        else:
            assert 0, "not implemented yet"
        self._emit_guard(op, locs[3:], c.NE)

    def emit_guard_class(self, op, arglocs, regalloc):
        self._cmp_guard_class(op, arglocs, regalloc)

    def emit_guard_nonnull_class(self, op, arglocs, regalloc):
        offset = self.cpu.vtable_offset
        if IS_PPC_32:
            self.mc.cmpwi(arglocs[0].value, 0)
        else:
            self.mc.cmpdi(arglocs[0].value, 0)
        if offset is not None:
            self._emit_guard(op, arglocs[3:], c.EQ)
        else:
            raise NotImplementedError
        self._cmp_guard_class(op, arglocs, regalloc)


class MiscOpAssembler(object):

    _mixin_ = True

    def emit_finish(self, op, arglocs, regalloc):
        self.gen_exit_stub(op.getdescr(), op.getarglist(), arglocs)

    def emit_jump(self, op, arglocs, regalloc):
        descr = op.getdescr()
        assert isinstance(descr, LoopToken)
        if descr._ppc_bootstrap_code == 0:
            curpos = self.mc.get_rel_pos()
            self.mc.b(descr._ppc_loop_code - curpos)
        else:
            target = descr._ppc_bootstrap_code + descr._ppc_loop_code
            self.mc.b_abs(target)
            new_fd = max(regalloc.frame_manager.frame_depth,
                         descr._ppc_frame_manager_depth)
            regalloc.frame_manager.frame_depth = new_fd

    def emit_same_as(self, op, arglocs, regalloc):
        argloc, resloc = arglocs
        self.regalloc_mov(argloc, resloc)

    emit_cast_ptr_to_int = emit_same_as
    emit_cast_int_to_ptr = emit_same_as

    def emit_call(self, op, args, regalloc, force_index=-1):
        adr = args[0].value
        arglist = op.getarglist()[1:]
        if force_index == -1:
            force_index = self.write_new_force_index()
        self._emit_call(force_index, adr, arglist, regalloc, op.result)
        descr = op.getdescr()
        #XXX Hack, Hack, Hack
        if op.result and not we_are_translated() and not isinstance(descr,
                LoopToken):
            #XXX check result type
            loc = regalloc.rm.call_result_location(op.result)
            size = descr.get_result_size(False)
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

        # adjust SP and compute size of parameter save area
        if IS_PPC_32:
            stack_space = BACKCHAIN_SIZE + len(stack_args) * WORD
            while stack_space % (4 * WORD) != 0:
                stack_space += 1
            self.mc.stwu(r.SP.value, r.SP.value, -stack_space)
            self.mc.mflr(r.r0.value)
            self.mc.stw(r.r0.value, r.SP.value, stack_space + WORD)
        else:
            # ABI fixed frame + 8 GPRs + arguments
            stack_space = (6 + MAX_REG_PARAMS + len(stack_args)) * WORD
            while stack_space % (2 * WORD) != 0:
                stack_space += 1
            self.mc.stdu(r.SP.value, r.SP.value, -stack_space)
            self.mc.mflr(r.r0.value)
            self.mc.std(r.r0.value, r.SP.value, stack_space + 2 * WORD)

        # then we push everything on the stack
        for i, arg in enumerate(stack_args):
            if IS_PPC_32:
                abi = 2
            else:
                abi = 14
            offset = (abi + i) * WORD
            if arg is not None:
                self.mc.load_imm(r.r0, arg.value)
            if IS_PPC_32:
                self.mc.stw(r.r0.value, r.SP.value, offset)
            else:
                self.mc.std(r.r0.value, r.SP.value, offset)

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
        remap_frame_layout(self, non_float_locs, non_float_regs, r.r0)

        #the actual call
        if IS_PPC_32:
            self.mc.bl_abs(adr)
            self.mc.lwz(r.r0.value, r.SP.value, stack_space + WORD)
        else:
            self.mc.std(r.r2.value, r.SP.value, 3 * WORD)
            self.mc.load_from_addr(r.r0, adr)
            self.mc.load_from_addr(r.r2, adr + WORD)
            self.mc.load_from_addr(r.r11, adr + 2 * WORD)
            self.mc.mtctr(r.r0.value)
            self.mc.bctrl()
            self.mc.ld(r.r2.value, r.SP.value, 3 * WORD)
            self.mc.ld(r.r0.value, r.SP.value, stack_space + 2 * WORD)
        self.mc.mtlr(r.r0.value)
        self.mc.addi(r.SP.value, r.SP.value, stack_space)

        self.mark_gc_roots(force_index)
        regalloc.possibly_free_vars(args)

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
            descr = op.getdescr()
            size =  descr.get_field_size(False)
            signed = descr.is_field_signed()
            self._ensure_result_bit_extension(res, size, signed)

    emit_getfield_raw = emit_getfield_gc
    emit_getfield_raw_pure = emit_getfield_gc
    emit_getfield_gc_pure = emit_getfield_gc


class ArrayOpAssembler(object):
    
    _mixin_ = True

    def emit_arraylen_gc(self, op, arglocs, regalloc):
        res, base_loc, ofs = arglocs
        if IS_PPC_32:
            self.mc.lwz(res.value, base_loc.value, ofs.value)
        else:
            self.mc.ld(res.value, base_loc.value, ofs.value)

    def emit_setarrayitem_gc(self, op, arglocs, regalloc):
        value_loc, base_loc, ofs_loc, scale, ofs, scratch_reg = arglocs
        if scale.value > 0:
            scale_loc = scratch_reg
            if IS_PPC_32:
                self.mc.slwi(scale_loc.value, ofs_loc.value, scale.value)
            else:
                self.mc.sldi(scale_loc.value, ofs_loc.value, scale.value)
        else:
            scale_loc = ofs_loc

        # add the base offset
        if ofs.value > 0:
            assert scale_loc is not r.r0
            self.mc.addi(r.r0.value, scale_loc.value, ofs.value)
            scale_loc = r.r0

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
        res, base_loc, ofs_loc, scale, ofs, scratch_reg = arglocs
        if scale.value > 0:
            scale_loc = scratch_reg
            if IS_PPC_32:
                self.mc.slwi(scale_loc.value, ofs_loc.value, scale.value)
            else:
                self.mc.sldi(scale_loc.value, ofs_loc.value, scale.value)
        else:
            scale_loc = ofs_loc

        # add the base offset
        if ofs.value > 0:
            assert scale_loc is not r.r0
            self.mc.addi(r.r0.value, scale_loc.value, ofs.value)
            scale_loc = r.r0

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
            size =  descr.get_item_size(False)
            signed = descr.is_item_signed()
            self._ensure_result_bit_extension(res, size, signed)

    emit_getarrayitem_raw = emit_getarrayitem_gc
    emit_getarrayitem_gc_pure = emit_getarrayitem_gc


class StrOpAssembler(object):

    _mixin_ = True

    def emit_strlen(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        if l1.is_imm():
            if IS_PPC_32:
                self.mc.lwz(res.value, l0.value, l1.getint())
            else:
                self.mc.ld(res.value, l0.value, l1.getint())
        else:
            if IS_PPC_32:
                self.mc.lwzx(res.value, l0.value, l1.value)
            else:
                self.mc.ldx(res.value, l0.value, l1.value)

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
        args = list(op.getarglist())
        base_loc, box = regalloc._ensure_value_is_boxed(args[0], args)
        args.append(box)
        ofs_loc, box = regalloc._ensure_value_is_boxed(args[2], args)
        args.append(box)
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
        base_loc, box = regalloc._ensure_value_is_boxed(args[1], forbidden_vars)
        args.append(box)
        forbidden_vars.append(box)
        ofs_loc, box = regalloc._ensure_value_is_boxed(args[3], forbidden_vars)
        args.append(box)
        assert base_loc.is_reg()
        assert ofs_loc.is_reg()
        regalloc.possibly_free_var(args[1])
        if args[3] is not args[4]:     # more of the MESS described above
            regalloc.possibly_free_var(args[3])
        self._gen_address_inside_string(base_loc, ofs_loc, dstaddr_loc,
                                        is_unicode=is_unicode)

        # compute the length in bytes
        forbidden_vars = [srcaddr_box, dstaddr_box]
        length_loc, length_box = regalloc._ensure_value_is_boxed(args[4], forbidden_vars)
        args.append(length_box)
        if is_unicode:
            forbidden_vars = [srcaddr_box, dstaddr_box]
            bytes_box = TempPtr()
            bytes_loc = regalloc.force_allocate_reg(bytes_box, forbidden_vars)
            scale = self._get_unicode_item_scale()
            assert length_loc.is_reg()
            self.mc.li(r.r0.value, 1<<scale)
            if IS_PPC_32:
                self.mc.mullw(bytes_loc.value, r.r0.value, length_loc.value)
            else:
                self.mc.mulld(bytes_loc.value, r.r0.value, length_loc.value)
            length_box = bytes_box
            length_loc = bytes_loc
        # call memcpy()
        self._emit_call(NO_FORCE_INDEX, self.memcpy_addr, 
                [dstaddr_box, srcaddr_box, length_box], regalloc)

        regalloc.possibly_free_vars(args)
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

    # from: ../x86/regalloc.py:750
    # called from regalloc
    # XXX kill this function at some point
    def _regalloc_malloc_varsize(self, size, size_box, vloc, vbox,
            ofs_items_loc, regalloc, result):
        if IS_PPC_32:
            self.mc.mullw(size.value, size.value, vloc.value)
        else:
            self.mc.mulld(size.value, size.value, vloc.value)
        if ofs_items_loc.is_imm():
            self.mc.addi(size.value, size.value, ofs_items_loc.value)
        else:
            self.mc.add(size.value, size.value, ofs_items_loc.value)
        force_index = self.write_new_force_index()
        regalloc.force_spill_var(vbox)
        self._emit_call(force_index, self.malloc_func_addr, [size_box], regalloc,
                                    result=result)

    def emit_new(self, op, arglocs, regalloc):
        # XXX do exception handling here!
        pass

    def emit_new_with_vtable(self, op, arglocs, regalloc):
        classint = arglocs[0].value
        self.set_vtable(op.result, classint)

    def set_vtable(self, box, vtable):
        if self.cpu.vtable_offset is not None:
            adr = rffi.cast(lltype.Signed, vtable)
            self.mc.load_imm(r.r0, adr)
            if IS_PPC_32:
                self.mc.stw(r.r0.value, r.r3.value, self.cpu.vtable_offset)
            else:
                self.mc.std(r.r0.value, r.r3.value, self.cpu.vtable_offset)

    def emit_new_array(self, op, arglocs, regalloc):
        # XXX handle memory errors
        if len(arglocs) > 0:
            value_loc, base_loc, ofs_length = arglocs
            if IS_PPC_32:
                self.mc.stw(value_loc.value, base_loc.value, ofs_length.value)
            else:
                self.mc.std(value_loc.value, base_loc.value, ofs_length.value)

    emit_newstr = emit_new_array
    emit_newunicode = emit_new_array


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


class ForceOpAssembler(object):

    _mixin_ = True

    def emit_guard_call_may_force(self, op, guard_op, arglocs, regalloc):
        self.mc.mr(r.r0.value, r.SP.value)
        if IS_PPC_32:
            self.mc.cmpwi(r.r0.value, 0)
        else:
            self.mc.cmpdi(r.r0.value, 0)
        self._emit_guard(guard_op, arglocs, c.EQ)

    emit_guard_call_release_gil = emit_guard_call_may_force


class OpAssembler(IntOpAssembler, GuardOpAssembler,
                  MiscOpAssembler, FieldOpAssembler,
                  ArrayOpAssembler, StrOpAssembler,
                  UnicodeOpAssembler, ForceOpAssembler,
                  AllocOpAssembler):

    def nop(self):
        self.mc.ori(0, 0, 0)

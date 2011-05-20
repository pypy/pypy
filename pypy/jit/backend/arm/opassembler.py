from pypy.jit.backend.arm import conditions as c
from pypy.jit.backend.arm import locations
from pypy.jit.backend.arm import registers as r
from pypy.jit.backend.arm import shift
from pypy.jit.backend.arm.arch import (WORD, FUNC_ALIGN, arm_int_div,
                                        arm_int_div_sign, arm_int_mod_sign,
                                        arm_int_mod, PC_OFFSET)

from pypy.jit.backend.arm.helper.assembler import (gen_emit_op_by_helper_call,
                                                    gen_emit_op_unary_cmp,
                                                    gen_emit_op_ri,
                                                    gen_emit_cmp_op,
                                                    gen_emit_float_op,
                                                    gen_emit_float_cmp_op,
                                                    gen_emit_unary_float_op, saved_registers)
from pypy.jit.backend.arm.codebuilder import ARMv7Builder, OverwritingBuilder
from pypy.jit.backend.arm.jump import remap_frame_layout
from pypy.jit.backend.arm.regalloc import Regalloc, TempInt, TempPtr
from pypy.jit.backend.llsupport import symbolic
from pypy.jit.backend.llsupport.descr import BaseFieldDescr, BaseArrayDescr
from pypy.jit.backend.llsupport.regalloc import compute_vars_longevity
from pypy.jit.metainterp.history import (Const, ConstInt, BoxInt, Box,
                                        AbstractFailDescr, LoopToken, INT, FLOAT, REF)
from pypy.jit.metainterp.resoperation import rop
from pypy.rlib import rgc
from pypy.rlib.objectmodel import we_are_translated
from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.lltypesystem import lltype, rffi, rstr, llmemory

class IntOpAsslember(object):

    _mixin_ = True

    def emit_op_int_add(self, op, arglocs, regalloc, fcond, flags=False):
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

    #ref: http://blogs.arm.com/software-enablement/detecting-overflow-from-mul/
    def emit_guard_int_mul_ovf(self, op, guard, arglocs, regalloc, fcond):
        reg1 = arglocs[0]
        reg2 = arglocs[1]
        res =  arglocs[2]
        failargs = arglocs[3:]
        self.mc.SMULL(res.value, r.ip.value, reg1.value, reg2.value, cond=fcond)
        self.mc.CMP_rr(r.ip.value, res.value, shifttype=shift.ASR, imm=31, cond=fcond)

        if guard.getopnum() == rop.GUARD_OVERFLOW:
            fcond = self._emit_guard(guard, failargs, c.NE)
        elif guard.getopnum() == rop.GUARD_NO_OVERFLOW:
            fcond = self._emit_guard(guard, failargs, c.EQ)
        else:
            assert 0
        return fcond

    def emit_guard_int_add_ovf(self, op, guard, arglocs, regalloc, fcond):
        self.emit_op_int_add(op, arglocs[0:3], regalloc, fcond, flags=True)
        self._emit_guard_overflow(guard, arglocs[3:], fcond)
        return fcond
    
    def emit_guard_int_sub_ovf(self, op, guard, arglocs, regalloc, fcond):
        self.emit_op_int_sub(op, arglocs[0:3], regalloc, fcond, flags=True)
        self._emit_guard_overflow(guard, arglocs[3:], fcond)
        return fcond

    emit_op_int_floordiv = gen_emit_op_by_helper_call('DIV')
    emit_op_int_mod = gen_emit_op_by_helper_call('MOD')
    emit_op_uint_floordiv = gen_emit_op_by_helper_call('UDIV')

    emit_op_int_and = gen_emit_op_ri('AND')
    emit_op_int_or = gen_emit_op_ri('ORR')
    emit_op_int_xor = gen_emit_op_ri('EOR')
    emit_op_int_lshift = gen_emit_op_ri('LSL')
    emit_op_int_rshift = gen_emit_op_ri('ASR')
    emit_op_uint_rshift = gen_emit_op_ri('LSR')

    emit_op_int_lt = gen_emit_cmp_op(c.LT)
    emit_op_int_le = gen_emit_cmp_op(c.LE)
    emit_op_int_eq = gen_emit_cmp_op(c.EQ)
    emit_op_int_ne = gen_emit_cmp_op(c.NE)
    emit_op_int_gt = gen_emit_cmp_op(c.GT)
    emit_op_int_ge = gen_emit_cmp_op(c.GE)

    emit_op_uint_le = gen_emit_cmp_op(c.LS)
    emit_op_uint_gt = gen_emit_cmp_op(c.HI)

    emit_op_uint_lt = gen_emit_cmp_op(c.HI)
    emit_op_uint_ge = gen_emit_cmp_op(c.LS)

    emit_op_int_add_ovf = emit_op_int_add
    emit_op_int_sub_ovf = emit_op_int_sub

    emit_op_ptr_eq = emit_op_int_eq
    emit_op_ptr_ne = emit_op_int_ne


class UnaryIntOpAssembler(object):

    _mixin_ = True

    emit_op_int_is_true = gen_emit_op_unary_cmp(c.NE, c.EQ)
    emit_op_int_is_zero = gen_emit_op_unary_cmp(c.EQ, c.NE)

    def emit_op_int_invert(self, op, arglocs, regalloc, fcond):
        reg, res = arglocs

        self.mc.MVN_rr(res.value, reg.value)
        return fcond

    def emit_op_int_neg(self, op, arglocs, regalloc, fcond):
        l0, resloc = arglocs
        self.mc.RSB_ri(resloc.value, l0.value, imm=0)
        return fcond

class GuardOpAssembler(object):

    _mixin_ = True

    guard_size = 5*WORD
    def _emit_guard(self, op, arglocs, fcond, save_exc=False):
        descr = op.getdescr()
        assert isinstance(descr, AbstractFailDescr)
        self.guard_descrs.append(descr)
        if not we_are_translated() and hasattr(op, 'getfailargs'):
           print 'Failargs: ', op.getfailargs()

        self.mc.ADD_ri(r.pc.value, r.pc.value, self.guard_size-PC_OFFSET, cond=fcond)
        descr._arm_guard_pos = self.mc.currpos()

        memaddr = self._gen_path_to_exit_path(op, op.getfailargs(),
                                            arglocs, save_exc=save_exc)
        descr._failure_recovery_code = memaddr
        return c.AL

    def _emit_guard_overflow(self, guard, failargs, fcond):
        if guard.getopnum() == rop.GUARD_OVERFLOW:
            fcond = self._emit_guard(guard, failargs, c.VS)
        elif guard.getopnum() == rop.GUARD_NO_OVERFLOW:
            fcond = self._emit_guard(guard, failargs, c.VC)
        else:
            assert 0
        return fcond

    def emit_op_guard_true(self, op, arglocs, regalloc, fcond):
        l0 = arglocs[0]
        failargs = arglocs[1:]
        self.mc.CMP_ri(l0.value, 0)
        fcond = self._emit_guard(op, failargs, c.NE)
        return fcond

    def emit_op_guard_false(self, op, arglocs, regalloc, fcond):
        l0 = arglocs[0]
        failargs = arglocs[1:]
        self.mc.CMP_ri(l0.value, 0)
        fcond = self._emit_guard(op, failargs, c.EQ)
        return fcond

    def emit_op_guard_value(self, op, arglocs, regalloc, fcond):
        l0 = arglocs[0]
        l1 = arglocs[1]
        failargs = arglocs[2:]

        if l0.is_reg():
            if l1.is_imm():
                self.mc.CMP_ri(l0.value, l1.getint())
            else:
                self.mc.CMP_rr(l0.value, l1.value)
        elif l0.is_vfp_reg():
            assert l1.is_vfp_reg()
            self.mc.VCMP(l0.value, l1.value)
            self.mc.VMRS(cond=fcond)
        fcond = self._emit_guard(op, failargs, c.EQ)
        return fcond

    emit_op_guard_nonnull = emit_op_guard_true
    emit_op_guard_isnull = emit_op_guard_false

    def emit_op_guard_no_overflow(self, op, arglocs, regalloc, fcond):
        return self._emit_guard(op, arglocs, c.VC)

    def emit_op_guard_overflow(self, op, arglocs, regalloc, fcond):
        return self._emit_guard(op, arglocs, c.VS)

    # from ../x86/assembler.py:1265
    def emit_op_guard_class(self, op, arglocs, regalloc, fcond):
        self._cmp_guard_class(op, arglocs, regalloc, fcond)
        return fcond

    def emit_op_guard_nonnull_class(self, op, arglocs, regalloc, fcond):
        offset = self.cpu.vtable_offset

        self.mc.CMP_ri(arglocs[0].value, 0)
        if offset is not None:
            self.mc.ADD_ri(r.pc.value, r.pc.value, 2*WORD, cond=c.EQ)
        else:
            raise NotImplementedError
        self._cmp_guard_class(op, arglocs, regalloc, fcond)
        return fcond

    def _cmp_guard_class(self, op, locs, regalloc, fcond):
        offset = locs[2]
        if offset is not None:
            if offset.is_imm():
                self.mc.LDR_ri(r.ip.value, locs[0].value, offset.value)
            else:
                assert offset.is_reg()
                self.mc.LDR_rr(r.ip.value, locs[0].value, offset.value)
            self.mc.CMP_rr(r.ip.value, locs[1].value)
        else:
            raise NotImplementedError
            # XXX port from x86 backend once gc support is in place

        return self._emit_guard(op, locs[3:], c.EQ)


class OpAssembler(object):

    _mixin_ = True

    def emit_op_jump(self, op, arglocs, regalloc, fcond):
        descr = op.getdescr()
        assert isinstance(descr, LoopToken)
        assert fcond == c.AL

        self._insert_checks()
        if descr._arm_bootstrap_code == 0:
            self.mc.B_offs(descr._arm_loop_code, fcond)
        else:
            target = descr._arm_bootstrap_code + descr._arm_loop_code
            self.mc.B(target, fcond)
            new_fd = max(regalloc.frame_manager.frame_depth, descr._arm_frame_depth)
            regalloc.frame_manager.frame_depth = new_fd
        return fcond

    def emit_op_finish(self, op, arglocs, regalloc, fcond):
        self._gen_path_to_exit_path(op, op.getarglist(), arglocs, c.AL)
        return fcond

    def emit_op_call(self, op, args, regalloc, fcond):
        adr = args[0].value
        arglist = op.getarglist()[1:]
        cond =  self._emit_call(adr, arglist, regalloc, fcond,
                                op.result)
        descr = op.getdescr()
        #XXX Hack, Hack, Hack
        if op.result and not we_are_translated() and not isinstance(descr, LoopToken):
            #XXX check result type
            loc = regalloc.rm.call_result_location(op.result)
            size = descr.get_result_size(False)
            signed = descr.is_result_signed()
            self._ensure_result_bit_extension(loc, size, signed)
        return cond

    # XXX improve this interface
    # emit_op_call_may_force
    # XXX improve freeing of stuff here
    def _emit_call(self, adr, args, regalloc, fcond=c.AL, result=None):
        n_args = len(args)
        #XXX replace with _count_reg_args
        reg_args = 0
        words = 0
        for x in range(min(n_args, 4)):
            if args[x].type == FLOAT:
                words += 2
            else:
                words += 1
            reg_args += 1
            if words > 4:
                reg_args = x
                break

        #spill all vars that are stored in caller saved registers
        #XXX good idea??
        vars_to_spill = []
        for v, reg in regalloc.rm.reg_bindings.iteritems():
            if reg in r.caller_resp:
                vars_to_spill.append(v)

        for v in vars_to_spill:
            regalloc.force_spill_var(v)
        # collect the locations of the arguments that go in the argument
        # registers
        locs = []
        for v in range(reg_args):
            var = args[v]
            loc = regalloc.loc(var)
            locs.append(loc)

        # save caller saved registers
        if result:
            if result.type == FLOAT:
                saved_regs = r.caller_resp[2:]
            else:
                saved_regs = r.caller_resp[1:]
        else:
            saved_regs = r.caller_resp


        # all arguments past the 4th go on the stack
        n = 0   # used to count the number of words pushed on the stack, so we
                #can later modify the SP back to its original value
        if n_args > reg_args:
            # first we need to prepare the list so it stays aligned
            stack_args = []
            count = 0
            for i in range(reg_args, n_args):
                arg = args[i]
                if arg.type != FLOAT:
                    count += 1
                    n += WORD
                else:
                    n += 2 * WORD
                    if count % 2 != 0:
                        stack_args.append(ConstInt(0))
                        n += WORD
                        count = 0
                stack_args.append(arg)
            if count % 2 != 0:
                n += WORD
                stack_args.append(ConstInt(0))
            #then we push every thing on the stack
            for i in range(len(stack_args) -1, -1, -1):
                arg = stack_args[i]
                if isinstance(arg, ConstInt) and arg.value == 0:
                    self.mc.PUSH([r.ip.value])
                else:
                    self.regalloc_push(regalloc.loc(arg))
        # move variables to the argument registers
        num = 0
        for i in range(reg_args):
            arg = args[i]
            reg = r.caller_resp[num]
            self.mov_loc_loc(locs[i], reg)
            if arg.type == FLOAT:
                num += 2
            else:
                num += 1

        regalloc.before_call(save_all_regs=2)
        #the actual call
        self.mc.BL(adr)
        regalloc.possibly_free_vars(args)
        # readjust the sp in case we passed some args on the stack
        if n_args > 4:
            assert n > 0
            self._adjust_sp(-n, fcond=fcond)

        # restore the argumets stored on the stack
        if result is not None:
            resloc = regalloc.after_call(result)
            # XXX ugly and fragile
            if result.type == FLOAT:
                # move result to the allocated register
                self.mov_loc_loc(r.r0, resloc)

        return fcond

    def emit_op_same_as(self, op, arglocs, regalloc, fcond):
        argloc, resloc = arglocs
        self.mov_loc_loc(argloc, resloc)
        return fcond

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
        self.mc.gen_load_int(loc.value, pos_exc_value.value, fcond)
        if resloc:
            self.mc.LDR_ri(resloc.value, loc.value)
        self.mc.MOV_ri(r.ip.value, 0)
        self.mc.STR_ri(r.ip.value, loc.value)
        self.mc.STR_ri(r.ip.value, loc1.value)
        return fcond

    def emit_op_debug_merge_point(self, op, arglocs, regalloc, fcond):
        return fcond
    emit_op_jit_debug = emit_op_debug_merge_point
    emit_op_cond_call_gc_wb = emit_op_debug_merge_point

class FieldOpAssembler(object):

    _mixin_ = True

    def emit_op_setfield_gc(self, op, arglocs, regalloc, fcond):
        value_loc, base_loc, ofs, size = arglocs
        if size.value == 8:
            assert value_loc.is_vfp_reg()
            if ofs.is_reg():
                base_loc = r.ip
                ofs = imm(0)
                self.mc.ADD_rr(r.ip.value, base_loc.value, ofs.value)
            self.mc.VSTR(value_loc.value, base_loc.value, ofs.value)
        elif size.value == 4:
            if ofs.is_imm():
                self.mc.STR_ri(value_loc.value, base_loc.value, ofs.value)
            else:
                self.mc.STR_rr(value_loc.value, base_loc.value, ofs.value)
        elif size.value == 2:
            if ofs.is_imm():
                self.mc.STRH_ri(value_loc.value, base_loc.value, ofs.value)
            else:
                self.mc.STRH_rr(value_loc.value, base_loc.value, ofs.value)
        elif size.value == 1:
            if ofs.is_imm():
                self.mc.STRB_ri(value_loc.value, base_loc.value, ofs.value)
            else:
                self.mc.STRB_rr(value_loc.value, base_loc.value, ofs.value)
        else:
            assert 0
        return fcond

    emit_op_setfield_raw = emit_op_setfield_gc

    def emit_op_getfield_gc(self, op, arglocs, regalloc, fcond):
        base_loc, ofs, res, size = arglocs
        if size.value == 8:
            assert res.is_vfp_reg()
            if ofs.is_reg():
                base_loc = r.ip
                ofs = imm(0)
                self.mc.ADD_rr(r.ip.value, base_loc.value, ofs.value)
            self.mc.VLDR(res.value, base_loc.value, ofs.value)
        elif size.value == 4:
            if ofs.is_imm():
                self.mc.LDR_ri(res.value, base_loc.value, ofs.value)
            else:
                self.mc.LDR_rr(res.value, base_loc.value, ofs.value)
        elif size.value == 2:
            if ofs.is_imm():
                self.mc.LDRH_ri(res.value, base_loc.value, ofs.value)
            else:
                self.mc.LDRH_rr(res.value, base_loc.value, ofs.value)
        elif size.value == 1:
            if ofs.is_imm():
                self.mc.LDRB_ri(res.value, base_loc.value, ofs.value)
            else:
                self.mc.LDRB_rr(res.value, base_loc.value, ofs.value)
        else:
            assert 0

        #XXX Hack, Hack, Hack
        if not we_are_translated():
            signed = op.getdescr().is_field_signed()
            self._ensure_result_bit_extension(res, size.value, signed)
        return fcond

    emit_op_getfield_raw = emit_op_getfield_gc
    emit_op_getfield_raw_pure = emit_op_getfield_gc
    emit_op_getfield_gc_pure = emit_op_getfield_gc




class ArrayOpAssember(object):

    _mixin_ = True

    def emit_op_arraylen_gc(self, op, arglocs, regalloc, fcond):
        res, base_loc, ofs = arglocs
        self.mc.LDR_ri(res.value, base_loc.value, ofs.value)
        return fcond

    def emit_op_setarrayitem_gc(self, op, arglocs, regalloc, fcond):
        value_loc, base_loc, ofs_loc, scale, ofs = arglocs

        if scale.value > 0:
            scale_loc = r.ip
            self.mc.LSL_ri(r.ip.value, ofs_loc.value, scale.value)
        else:
            scale_loc = ofs_loc

        if ofs.value > 0:
            self.mc.ADD_ri(r.ip.value, scale_loc.value, ofs.value)
            scale_loc = r.ip

        if scale.value == 3:
            assert value_loc.is_vfp_reg()
            assert scale_loc.is_reg()
            self.mc.ADD_rr(r.ip.value, base_loc.value, scale_loc.value)
            self.mc.VSTR(value_loc.value, r.ip.value, cond=fcond)
        elif scale.value == 2:
            self.mc.STR_rr(value_loc.value, base_loc.value, scale_loc.value, cond=fcond)
        elif scale.value == 1:
            self.mc.STRH_rr(value_loc.value, base_loc.value, scale_loc.value, cond=fcond)
        elif scale.value == 0:
            self.mc.STRB_rr(value_loc.value, base_loc.value, scale_loc.value, cond=fcond)
        else:
            assert 0
        return fcond

    emit_op_setarrayitem_raw = emit_op_setarrayitem_gc

    def emit_op_getarrayitem_gc(self, op, arglocs, regalloc, fcond):
        res, base_loc, ofs_loc, scale, ofs = arglocs
        if scale.value > 0:
            scale_loc = r.ip
            self.mc.LSL_ri(r.ip.value, ofs_loc.value, scale.value)
        else:
            scale_loc = ofs_loc
        if ofs.value > 0:
            self.mc.ADD_ri(r.ip.value, scale_loc.value, imm=ofs.value)
            scale_loc = r.ip

        if scale.value == 3:
            assert res.is_vfp_reg()
            assert scale_loc.is_reg()
            self.mc.ADD_rr(r.ip.value, base_loc.value, scale_loc.value)
            self.mc.VLDR(res.value, r.ip.value, cond=fcond)
        elif scale.value == 2:
            self.mc.LDR_rr(res.value, base_loc.value, scale_loc.value, cond=fcond)
        elif scale.value == 1:
            self.mc.LDRH_rr(res.value, base_loc.value, scale_loc.value, cond=fcond)
        elif scale.value == 0:
            self.mc.LDRB_rr(res.value, base_loc.value, scale_loc.value, cond=fcond)
        else:
            assert 0

        #XXX Hack, Hack, Hack
        if not we_are_translated():
            descr = op.getdescr()
            size =  descr.get_item_size(False)
            signed = descr.is_item_signed()
            self._ensure_result_bit_extension(res, size, signed)
        return fcond

    emit_op_getarrayitem_raw = emit_op_getarrayitem_gc
    emit_op_getarrayitem_gc_pure = emit_op_getarrayitem_gc


class StrOpAssembler(object):

    _mixin_ = True

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
            self.mc.ADD_ri(r.ip.value, base_loc.value, ofs_loc.getint(), cond=fcond)
        else:
            self.mc.ADD_rr(r.ip.value, base_loc.value, ofs_loc.value, cond=fcond)

        self.mc.LDRB_ri(res.value, r.ip.value, basesize.value, cond=fcond)
        return fcond

    def emit_op_strsetitem(self, op, arglocs, regalloc, fcond):
        value_loc, base_loc, ofs_loc, basesize = arglocs
        if ofs_loc.is_imm():
            self.mc.ADD_ri(r.ip.value, base_loc.value, ofs_loc.getint(), cond=fcond)
        else:
            self.mc.ADD_rr(r.ip.value, base_loc.value, ofs_loc.value, cond=fcond)

        self.mc.STRB_ri(value_loc.value, r.ip.value, basesize.value, cond=fcond)
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
        srcaddr_loc = regalloc.force_allocate_reg(srcaddr_box, selected_reg=r.r1)
        self._gen_address_inside_string(base_loc, ofs_loc, srcaddr_loc,
                                        is_unicode=is_unicode)

        # compute the destination address
        forbidden_vars = [args[4], args[3], srcaddr_box]
        dstaddr_box = TempPtr()
        dstaddr_loc = regalloc.force_allocate_reg(dstaddr_box, selected_reg=r.r0)
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
            self.mc.MOV_ri(r.ip.value, 1<<scale)
            self.mc.MUL(bytes_loc.value, r.ip.value, length_loc.value)
            length_box = bytes_box
            length_loc = bytes_loc
        # call memcpy()
        self._emit_call(self.memcpy_addr, [dstaddr_box, srcaddr_box, length_box], regalloc)

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
            scaled_loc = r.ip
            self.mc.LSL_ri(r.ip.value, sizereg.value, scale)
        else:
            scaled_loc = sizereg
        if baseloc is not None:
            assert baseloc.is_reg()
            self.mc.ADD_rr(result.value, baseloc.value, scaled_loc.value)
            self.mc.ADD_ri(result.value, result.value, baseofs)
        else:
            self.mc.ADD_ri(result.value, scaled_loc.value, baseofs)

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

    emit_op_unicodelen = StrOpAssembler.emit_op_strlen

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
            self.mc.STR_ri(value_loc.value, r.ip.value, basesize.value, cond=fcond)
        elif scale.value == 1:
            self.mc.STRH_ri(value_loc.value, r.ip.value, basesize.value, cond=fcond)
        else:
            assert 0, itemsize.value

        return fcond

class ForceOpAssembler(object):

    _mixin_ = True

    def emit_op_force_token(self, op, arglocs, regalloc, fcond):
        res_loc = arglocs[0]
        self.mc.MOV_rr(res_loc.value, r.fp.value)
        return fcond

    # from: ../x86/assembler.py:1668
    # XXX Split into some helper methods
    def emit_guard_call_assembler(self, op, guard_op, arglocs, regalloc, fcond):
        faildescr = guard_op.getdescr()
        fail_index = self.cpu.get_fail_descr_number(faildescr)
        self._write_fail_index(fail_index)

        descr = op.getdescr()
        assert isinstance(descr, LoopToken)
        # XXX check this
        assert op.numargs() == len(descr._arm_arglocs[0])
        resbox = TempInt()
        self._emit_call(descr._arm_direct_bootstrap_code, op.getarglist(),
                                regalloc, fcond, result=resbox)
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
        # check value
        resloc = regalloc.try_allocate_reg(resbox)
        assert resloc is r.r0
        self.mc.gen_load_int(r.ip.value, value)
        self.mc.CMP_rr(resloc.value, r.ip.value)
        regalloc.possibly_free_var(resbox)

        fast_jmp_pos = self.mc.currpos()
        self.mc.NOP()

        # Path A: use assembler helper
        #if values are equal we take the fast path
        # Slow path, calling helper
        # jump to merge point
        jd = descr.outermost_jitdriver_sd
        assert jd is not None
        asm_helper_adr = self.cpu.cast_adr_to_int(jd.assembler_helper_adr)
        with saved_registers(self.mc, r.caller_resp[1:], r.caller_vfp_resp, regalloc=regalloc):
            # resbox is allready in r0
            self.mov_loc_loc(arglocs[1], r.r1)
            self.mc.BL(asm_helper_adr)
            if op.result:
                resloc = regalloc.after_call(op.result)
                # XXX ugly and fragile
                if op.result.type == FLOAT:
                    # move result to the allocated register
                    self.mov_loc_loc(r.r0, resloc)

        # jump to merge point
        jmp_pos = self.mc.currpos()
        #jmp_location = self.mc.curraddr()
        self.mc.NOP()

        # Path B: load return value and reset token
        # Fast Path using result boxes
        # patch the jump to the fast path
        offset = self.mc.currpos() - fast_jmp_pos
        pmc = OverwritingBuilder(self.mc, fast_jmp_pos, WORD)
        pmc.ADD_ri(r.pc.value, r.pc.value, offset - PC_OFFSET, cond=c.EQ)

        # Reset the vable token --- XXX really too much special logic here:-(
        if jd.index_of_virtualizable >= 0:
            from pypy.jit.backend.llsupport.descr import BaseFieldDescr
            fielddescr = jd.vable_token_descr
            assert isinstance(fielddescr, BaseFieldDescr)
            ofs = fielddescr.offset
            resloc = regalloc.force_allocate_reg(resbox)
            self.mov_loc_loc(arglocs[1], r.ip)
            self.mc.MOV_ri(resloc.value, 0)
            self.mc.STR_ri(resloc.value, r.ip.value, ofs)
            regalloc.possibly_free_var(resbox)

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
            resloc = regalloc.force_allocate_reg(op.result)
            regalloc.possibly_free_var(resbox)
            self.mc.gen_load_int(r.ip.value, adr)
            if op.result.type == FLOAT:
                self.mc.VLDR(resloc.value, r.ip.value)
            else:
                self.mc.LDR_ri(resloc.value, r.ip.value)

        # merge point
        offset = self.mc.currpos() - jmp_pos
        if offset - PC_OFFSET >= 0:
            pmc = OverwritingBuilder(self.mc, jmp_pos, WORD)
            pmc.ADD_ri(r.pc.value, r.pc.value, offset - PC_OFFSET)

        self.mc.LDR_ri(r.ip.value, r.fp.value)
        self.mc.CMP_ri(r.ip.value, 0)

        self._emit_guard(guard_op, regalloc._prepare_guard(guard_op), c.GE)
        return fcond


    # ../x86/assembler.py:668
    def redirect_call_assembler(self, oldlooptoken, newlooptoken):
        # we overwrite the instructions at the old _x86_direct_bootstrap_code
        # to start with a JMP to the new _x86_direct_bootstrap_code.
        # Ideally we should rather patch all existing CALLs, but well.
        oldadr = oldlooptoken._arm_direct_bootstrap_code
        target = newlooptoken._arm_direct_bootstrap_code
        mc = ARMv7Builder()
        mc.B(target)
        mc.copy_to_raw_memory(oldadr)

    def emit_guard_call_may_force(self, op, guard_op, arglocs, regalloc, fcond):
        self.mc.LDR_ri(r.ip.value, r.fp.value)
        self.mc.CMP_ri(r.ip.value, 0)

        self._emit_guard(guard_op, arglocs, c.GE)
        return fcond

    def _write_fail_index(self, fail_index):
        self.mc.gen_load_int(r.ip.value, fail_index)
        self.mc.STR_ri(r.ip.value, r.fp.value)

class AllocOpAssembler(object):

    _mixin_ = True


    # from: ../x86/regalloc.py:750
    # called from regalloc
    # XXX kill this function at some point
    def _regalloc_malloc_varsize(self, size, size_box, vloc, ofs_items_loc, regalloc, result):
        self.mc.MUL(size.value, size.value, vloc.value)
        if ofs_items_loc.is_imm():
            self.mc.ADD_ri(size.value, size.value, ofs_items_loc.value)
        else:
            self.mc.ADD_rr(size.value, size.value, ofs_items_loc.value)
        self._emit_call(self.malloc_func_addr, [size_box], regalloc,
                                    result=result)

    def emit_op_new(self, op, arglocs, regalloc, fcond):
        return fcond

    def emit_op_new_with_vtable(self, op, arglocs, regalloc, fcond):
        classint = arglocs[0].value
        self.set_vtable(op.result, classint)
        return fcond

    def set_vtable(self, box, vtable):
        if self.cpu.vtable_offset is not None:
            adr = rffi.cast(lltype.Signed, vtable)
            self.mc.gen_load_int(r.ip.value, adr)
            self.mc.STR_ri(r.ip.value, r.r0.value, self.cpu.vtable_offset)

    def set_new_array_length(self, loc, ofs_length, loc_num_elem):
        assert loc.is_reg()
        self.mc.gen_load_int(r.ip.value, loc_num_elem)
        self.mc.STR_ri(r.ip.value, loc.value, imm=ofs_length)

    def emit_op_new_array(self, op, arglocs, regalloc, fcond):
        if len(arglocs) > 0:
            value_loc, base_loc, ofs_length = arglocs
            self.mc.STR_ri(value_loc.value, base_loc.value, ofs_length.value)
        return fcond

    emit_op_newstr = emit_op_new_array
    emit_op_newunicode = emit_op_new_array

class FloatOpAssemlber(object):
    _mixin_ = True

    emit_op_float_add = gen_emit_float_op('VADD')
    emit_op_float_sub = gen_emit_float_op('VSUB')
    emit_op_float_mul = gen_emit_float_op('VMUL')
    emit_op_float_truediv = gen_emit_float_op('VDIV')

    emit_op_float_neg = gen_emit_unary_float_op('VNEG')
    emit_op_float_abs = gen_emit_unary_float_op('VABS')

    emit_op_float_lt = gen_emit_float_cmp_op(c.VFP_LT)
    emit_op_float_le = gen_emit_float_cmp_op(c.VFP_LE)
    emit_op_float_eq = gen_emit_float_cmp_op(c.EQ)
    emit_op_float_ne = gen_emit_float_cmp_op(c.NE)
    emit_op_float_gt = gen_emit_float_cmp_op(c.GT)
    emit_op_float_ge = gen_emit_float_cmp_op(c.GE)

    def emit_op_cast_float_to_int(self, op, arglocs, regalloc, fcond):
        arg, temp, res = arglocs
        self.mc.VCVT_float_to_int(temp.value, arg.value)
        self.mc.VPUSH([temp.value])
        # res is lower register than r.ip
        self.mc.POP([res.value, r.ip.value])
        return fcond

    def emit_op_cast_int_to_float(self, op, arglocs, regalloc, fcond):
        arg, temp, res = arglocs
        self.mc.PUSH([arg.value, r.ip.value])
        self.mc.VPOP([temp.value])
        self.mc.VCVT_int_to_float(res.value, temp.value)
        return fcond

class ResOpAssembler(GuardOpAssembler, IntOpAsslember,
                    OpAssembler, UnaryIntOpAssembler,
                    FieldOpAssembler, ArrayOpAssember,
                    StrOpAssembler, UnicodeOpAssembler,
                    ForceOpAssembler, AllocOpAssembler,
                    FloatOpAssemlber):
    pass


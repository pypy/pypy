from pypy.jit.backend.arm import conditions as c
from pypy.jit.backend.arm import locations
from pypy.jit.backend.arm import registers as r
from pypy.jit.backend.arm import shift
from pypy.jit.backend.arm.arch import (WORD, FUNC_ALIGN, arm_int_div,
                                        arm_int_div_sign, arm_int_mod_sign,
                                        arm_int_mod, PC_OFFSET)

from pypy.jit.backend.arm.helper.assembler import (gen_emit_op_by_helper_call,
                                                    gen_emit_op_unary_cmp,
                                                    gen_emit_op_ri, gen_emit_cmp_op)
from pypy.jit.backend.arm.codebuilder import ARMv7Builder, ARMv7InMemoryBuilder
from pypy.jit.backend.arm.jump import remap_frame_layout
from pypy.jit.backend.arm.regalloc import ARMRegisterManager
from pypy.jit.backend.llsupport import symbolic
from pypy.jit.backend.llsupport.descr import BaseFieldDescr, BaseArrayDescr
from pypy.jit.backend.llsupport.regalloc import compute_vars_longevity, TempBox
from pypy.jit.codewriter import heaptracker
from pypy.jit.metainterp.history import (Const, ConstInt, BoxInt, Box,
                                        AbstractFailDescr, LoopToken, INT, FLOAT, REF)
from pypy.jit.metainterp.resoperation import rop
from pypy.rlib import rgc
from pypy.rlib.objectmodel import we_are_translated
from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.lltypesystem import lltype, rffi, rstr, llmemory

class IntOpAsslember(object):

    _mixin_ = True

    def emit_op_int_add(self, op, regalloc, fcond):
        #XXX check if neg values are supported for imm values
        boxes = list(op.getarglist())
        a0, a1 = boxes
        imm_a0 = self._check_imm_arg(a0)
        imm_a1 = self._check_imm_arg(a1)
        if not imm_a0 and imm_a1:
            l0, box = self._ensure_value_is_boxed(a0, regalloc, boxes)
            l1 = regalloc.make_sure_var_in_reg(a1, [a0])
            boxes.append(box)
        elif imm_a0 and not imm_a1:
            l0 = regalloc.make_sure_var_in_reg(a0)
            l1, box = self._ensure_value_is_boxed(a1, regalloc, boxes)
            boxes.append(box)
        else:
            l0, box = self._ensure_value_is_boxed(a0, regalloc, boxes)
            boxes.append(box)
            l1, box = self._ensure_value_is_boxed(a1, regalloc, boxes)
            boxes.append(box)
        res = regalloc.force_allocate_reg(op.result, boxes)

        if l0.is_imm():
            self.mc.ADD_ri(res.value, l1.value, imm=l0.value, s=1)
        elif l1.is_imm():
            self.mc.ADD_ri(res.value, l0.value, imm=l1.value, s=1)
        else:
            self.mc.ADD_rr(res.value, l0.value, l1.value, s=1)

        regalloc.possibly_free_vars(boxes)
        regalloc.possibly_free_var(op.result)
        return fcond

    def emit_op_int_sub(self, op, regalloc, fcond):
        #XXX check if neg values are supported for imm values
        boxes = list(op.getarglist())
        a0, a1 = boxes
        imm_a0 = self._check_imm_arg(a0)
        imm_a1 = self._check_imm_arg(a1)
        if not imm_a0 and imm_a1:
            l0, box = self._ensure_value_is_boxed(a0, regalloc, boxes)
            l1 = regalloc.make_sure_var_in_reg(a1, [a0])
            boxes.append(box)
        elif imm_a0 and not imm_a1:
            l0 = regalloc.make_sure_var_in_reg(a0)
            l1, box = self._ensure_value_is_boxed(a1, regalloc, boxes)
            boxes.append(box)
        else:
            l0, box = self._ensure_value_is_boxed(a0, regalloc, boxes)
            boxes.append(box)
            l1, box = self._ensure_value_is_boxed(a1, regalloc, boxes)
            boxes.append(box)
        res = regalloc.force_allocate_reg(op.result, boxes)
        if l0.is_imm():
            value = l0.getint()
            assert value >= 0
            # reverse substract ftw
            self.mc.RSB_ri(res.value, l1.value, value, s=1)
        elif l1.is_imm():
            value = l1.getint()
            assert value >= 0
            self.mc.SUB_ri(res.value, l0.value, value, s=1)
        else:
            self.mc.SUB_rr(res.value, l0.value, l1.value, s=1)

        regalloc.possibly_free_vars(boxes)
        regalloc.possibly_free_var(op.result)
        return fcond

    def emit_op_int_mul(self, op, regalloc, fcond):
        boxes = list(op.getarglist())
        a0, a1 = boxes

        reg1, box = self._ensure_value_is_boxed(a0, regalloc, forbidden_vars=boxes)
        boxes.append(box)
        reg2, box = self._ensure_value_is_boxed(a1, regalloc, forbidden_vars=boxes)
        boxes.append(box)

        res = regalloc.force_allocate_reg(op.result, boxes)
        self.mc.MUL(res.value, reg1.value, reg2.value)
        regalloc.possibly_free_vars(boxes)
        regalloc.possibly_free_var(op.result)
        return fcond

    #ref: http://blogs.arm.com/software-enablement/detecting-overflow-from-mul/
    def emit_guard_int_mul_ovf(self, op, guard, regalloc, fcond):
        boxes = list(op.getarglist())
        a0, a1 = boxes

        reg1, box = self._ensure_value_is_boxed(a0, regalloc, forbidden_vars=boxes)
        boxes.append(box)
        reg2, box = self._ensure_value_is_boxed(a1, regalloc, forbidden_vars=boxes)
        boxes.append(box)
        res = regalloc.force_allocate_reg(op.result, boxes)

        self.mc.SMULL(res.value, r.ip.value, reg1.value, reg2.value, cond=fcond)
        self.mc.CMP_rr(r.ip.value, res.value, shifttype=shift.ASR, imm=31, cond=fcond)
        regalloc.possibly_free_vars(boxes)
        regalloc.possibly_free_var(op.result)

        if guard.getopnum() == rop.GUARD_OVERFLOW:
            return self._emit_guard(guard, regalloc, c.NE)
        if guard.getopnum() == rop.GUARD_NO_OVERFLOW:
            return self._emit_guard(guard, regalloc, c.EQ)
        else:
            assert 0

    emit_op_int_floordiv = gen_emit_op_by_helper_call('DIV')
    emit_op_int_mod = gen_emit_op_by_helper_call('MOD')
    emit_op_uint_floordiv = gen_emit_op_by_helper_call('UDIV')

    emit_op_int_and = gen_emit_op_ri('AND')
    emit_op_int_or = gen_emit_op_ri('ORR')
    emit_op_int_xor = gen_emit_op_ri('EOR')
    emit_op_int_lshift = gen_emit_op_ri('LSL', imm_size=0x1F, allow_zero=False, commutative=False)
    emit_op_int_rshift = gen_emit_op_ri('ASR', imm_size=0x1F, allow_zero=False, commutative=False)
    emit_op_uint_rshift = gen_emit_op_ri('LSR', imm_size=0x1F, allow_zero=False, commutative=False)

    emit_op_int_lt = gen_emit_cmp_op(c.LT)
    emit_op_int_le = gen_emit_cmp_op(c.LE)
    emit_op_int_eq = gen_emit_cmp_op(c.EQ)
    emit_op_int_ne = gen_emit_cmp_op(c.NE)
    emit_op_int_gt = gen_emit_cmp_op(c.GT)
    emit_op_int_ge = gen_emit_cmp_op(c.GE)

    emit_op_uint_le = gen_emit_cmp_op(c.LS)
    emit_op_uint_gt = gen_emit_cmp_op(c.HI)

    emit_op_uint_lt = gen_emit_cmp_op(c.HI, inverse=True)
    emit_op_uint_ge = gen_emit_cmp_op(c.LS, inverse=True)

    emit_op_int_add_ovf = emit_op_int_add
    emit_op_int_sub_ovf = emit_op_int_sub

    emit_op_ptr_eq = emit_op_int_eq
    emit_op_ptr_ne = emit_op_int_ne



class UnaryIntOpAssembler(object):

    _mixin_ = True

    emit_op_int_is_true = gen_emit_op_unary_cmp(c.NE, c.EQ)
    emit_op_int_is_zero = gen_emit_op_unary_cmp(c.EQ, c.NE)

    def emit_op_int_invert(self, op, regalloc, fcond):
        reg, box = self._ensure_value_is_boxed(op.getarg(0), regalloc)
        res = regalloc.force_allocate_reg(op.result, [box])
        regalloc.possibly_free_var(box)
        regalloc.possibly_free_var(op.result)

        self.mc.MVN_rr(res.value, reg.value)
        return fcond

    #XXX check for a better way of doing this
    def emit_op_int_neg(self, op, regalloc, fcond):
        l0, box = self._ensure_value_is_boxed(op.getarg(0), regalloc)
        resloc = regalloc.force_allocate_reg(op.result, [box])
        regalloc.possibly_free_vars([box, op.result])

        self.mc.MVN_ri(r.ip.value, imm=~-1)
        self.mc.MUL(resloc.value, l0.value, r.ip.value)
        return fcond

class GuardOpAssembler(object):

    _mixin_ = True

    guard_size = 10*WORD
    def _emit_guard(self, op, regalloc, fcond, save_exc=False):
        descr = op.getdescr()
        assert isinstance(descr, AbstractFailDescr)
        if not we_are_translated() and hasattr(op, 'getfailargs'):
           print 'Failargs: ', op.getfailargs()

        self.mc.ensure_can_fit(self.guard_size)
        self.mc.ADD_ri(r.pc.value, r.pc.value, self.guard_size-PC_OFFSET, cond=fcond)
        descr._arm_guard_code = self.mc.curraddr()

        self.mc.PUSH([reg.value for reg in r.caller_resp])
        addr = self.cpu.get_on_leave_jitted_int(save_exception=save_exc)
        self.mc.BL(addr)
        self.mc.POP([reg.value for reg in r.caller_resp])

        memaddr = self._gen_path_to_exit_path(op, op.getfailargs(), regalloc)
        descr._failure_recovery_code = memaddr
        regalloc.possibly_free_vars_for_op(op)
        return c.AL

    def emit_op_guard_true(self, op, regalloc, fcond):
        l0, box = self._ensure_value_is_boxed(op.getarg(0), regalloc)
        regalloc.possibly_free_var(box)
        self.mc.CMP_ri(l0.value, 0)
        return self._emit_guard(op, regalloc, c.NE)

    def emit_op_guard_false(self, op, regalloc, fcond):
        l0, box = self._ensure_value_is_boxed(op.getarg(0), regalloc)
        regalloc.possibly_free_var(box)
        self.mc.CMP_ri(l0.value, 0)
        return self._emit_guard(op, regalloc, c.EQ)

    def emit_op_guard_value(self, op, regalloc, fcond):
        boxes = list(op.getarglist())
        a0, a1 = boxes
        imm_a1 = self._check_imm_arg(a1)
        l0, box = self._ensure_value_is_boxed(a0, regalloc, boxes)
        boxes.append(box)
        if not imm_a1:
            l1, box = self._ensure_value_is_boxed(a1, regalloc, boxes)
            boxes.append(box)
        else:
            l1 = regalloc.make_sure_var_in_reg(a1)
        regalloc.possibly_free_vars(boxes)
        regalloc.possibly_free_var(op.result)

        if l1.is_imm():
            self.mc.CMP_ri(l0.value, l1.getint())
        else:
            self.mc.CMP_rr(l0.value, l1.value)
        return self._emit_guard(op, regalloc, c.EQ)

    emit_op_guard_nonnull = emit_op_guard_true
    emit_op_guard_isnull = emit_op_guard_false

    def emit_op_guard_no_overflow(self, op, regalloc, fcond):
        return self._emit_guard(op, regalloc, c.VC)

    def emit_op_guard_overflow(self, op, regalloc, fcond):
        return self._emit_guard(op, regalloc, c.VS)

    # from ../x86/assembler.py:1265
    def emit_op_guard_class(self, op, regalloc, fcond):
        locs = self._prepare_guard_class(op, regalloc, fcond)
        self._cmp_guard_class(op, locs, regalloc, fcond)
        return fcond

    def emit_op_guard_nonnull_class(self, op, regalloc, fcond):
        offset = self.cpu.vtable_offset
        if offset is not None:
            self.mc.ensure_can_fit(self.guard_size+3*WORD)
        else:
            raise NotImplementedError
        locs = self._prepare_guard_class(op, regalloc, fcond)

        self.mc.CMP_ri(locs[0].value, 0)
        if offset is not None:
            self.mc.ADD_ri(r.pc.value, r.pc.value, 2*WORD, cond=c.EQ)
        else:
            raise NotImplementedError
        self._cmp_guard_class(op, locs, regalloc, fcond)
        return fcond

    def _prepare_guard_class(self, op, regalloc, fcond):
        assert isinstance(op.getarg(0), Box)
        boxes = list(op.getarglist())

        x, x_box = self._ensure_value_is_boxed(boxes[0], regalloc, boxes)
        boxes.append(x_box)

        t = TempBox()
        y = regalloc.force_allocate_reg(t, boxes)
        boxes.append(t)
        y_val = op.getarg(1).getint()
        self.mc.gen_load_int(y.value, rffi.cast(lltype.Signed, y_val))

        regalloc.possibly_free_vars(boxes)
        return [x, y]


    def _cmp_guard_class(self, op, locs, regalloc, fcond):
        offset = self.cpu.vtable_offset
        x, y = locs
        if offset is not None:
            assert offset == 0
            self.mc.LDR_ri(r.ip.value, x.value, offset)
            self.mc.CMP_rr(r.ip.value, y.value)
        else:
            raise NotImplementedError
            # XXX port from x86 backend once gc support is in place

        return self._emit_guard(op, regalloc, c.EQ)



class OpAssembler(object):

    _mixin_ = True

    def emit_op_jump(self, op, regalloc, fcond):
        descr = op.getdescr()
        assert isinstance(descr, LoopToken)
        destlocs = descr._arm_arglocs
        srclocs  = [regalloc.loc(op.getarg(i)) for i in range(op.numargs())]
        remap_frame_layout(self, srclocs, destlocs, r.ip)

        loop_code = descr._arm_loop_code
        self.mc.B(loop_code, fcond)
        return fcond

    def emit_op_finish(self, op, regalloc, fcond):
        self._gen_path_to_exit_path(op, op.getarglist(), regalloc, c.AL)
        return fcond

    def emit_op_call(self, op, regalloc, fcond, save_all_regs=False):
        adr = rffi.cast(lltype.Signed, op.getarg(0).getint())
        args = op.getarglist()[1:]
        cond =  self._emit_call(adr, args, regalloc, fcond, save_all_regs, op.result)
        if op.result:
            regalloc.possibly_free_var(op.result)

        descr = op.getdescr()
        #XXX Hack, Hack, Hack
        if op.result and not we_are_translated() and not isinstance(descr, LoopToken):
            loc = regalloc.loc(op.result)
            size = descr.get_result_size(False)
            signed = descr.is_result_signed()
            self._ensure_result_bit_extension(loc, size, signed, regalloc)
        return cond

    def _emit_call(self, adr, args, regalloc, fcond=c.AL, save_all_regs=False, result=None):
        # all arguments past the 4th go on the stack
        n = 0
        n_args = len(args)
        if n_args > 4:
            stack_args = n_args - 4
            n = stack_args*WORD
            self._adjust_sp(n, regalloc, fcond=fcond)
            for i in range(4, n_args):
                reg, box = self._ensure_value_is_boxed(args[i], regalloc)
                self.mc.STR_ri(reg.value, r.sp.value, (i-4)*WORD)
                regalloc.possibly_free_var(box)


        reg_args = min(n_args, 4)
        for i in range(0, reg_args):
            l = regalloc.make_sure_var_in_reg(args[i],
                                            selected_reg=r.all_regs[i])
        # XXX use PUSH here instead of spilling every reg for itself
        regalloc.before_call(save_all_regs=save_all_regs)
        regalloc.possibly_free_vars(args)

        self.mc.BL(adr)

        if result:
            regalloc.after_call(result)
        # readjust the sp in case we passed some args on the stack
        if n_args > 4:
            assert n > 0
            self._adjust_sp(-n, regalloc, fcond=fcond)
        return fcond

    def emit_op_same_as(self, op, regalloc, fcond):
        resloc = regalloc.force_allocate_reg(op.result)
        arg = op.getarg(0)
        imm_arg = self._check_imm_arg(arg)
        argloc = regalloc.make_sure_var_in_reg(arg, [op.result], imm_fine=imm_arg)
        if argloc.is_imm():
            self.mc.MOV_ri(resloc.value, argloc.getint())
        else:
            self.mc.MOV_rr(resloc.value, argloc.value)
        regalloc.possibly_free_vars_for_op(op)
        regalloc.possibly_free_var(op.result)
        return fcond

    def emit_op_cond_call_gc_wb(self, op, regalloc, fcond):
        #XXX implement once gc support is in place
        return fcond

    def emit_op_guard_no_exception(self, op, regalloc, fcond):
        t = TempBox()
        loc = regalloc.force_allocate_reg(t)
        self.mc.gen_load_int(loc.value, self.cpu.pos_exception(), fcond)
        self.mc.LDR_ri(loc.value, loc.value)
        self.mc.CMP_ri(loc.value, 0)
        cond = self._emit_guard(op, regalloc, c.EQ, save_exc=True)
        regalloc.possibly_free_var(t)
        return cond

    def emit_op_guard_exception(self, op, regalloc, fcond):
        args = op.getarglist()
        t = TempBox()
        t1 = TempBox()
        loc = regalloc.force_allocate_reg(t, args)
        loc1 = regalloc.force_allocate_reg(t1, args + [t])
        self.mc.gen_load_int(loc.value,
                rffi.cast(lltype.Signed, op.getarg(0).getint()),
                fcond)

        self.mc.gen_load_int(loc1.value, self.cpu.pos_exception(), fcond)
        self.mc.LDR_ri(loc1.value, loc1.value)

        self.mc.CMP_rr(loc1.value, loc.value)
        self._emit_guard(op, regalloc, c.EQ, save_exc=True)
        self.mc.gen_load_int(loc1.value, self.cpu.pos_exc_value(), fcond)
        if op.result in regalloc.longevity:
            resloc = regalloc.force_allocate_reg(op.result, args + [t, t1])
            self.mc.LDR_ri(resloc.value, loc1.value)
            regalloc.possibly_free_var(op.result)
        self.mc.gen_load_int(loc.value, self.cpu.pos_exception(), fcond)
        self.mc.MOV_ri(r.ip.value, 0)
        self.mc.STR_ri(r.ip.value, loc.value)
        self.mc.STR_ri(r.ip.value, loc1.value)
        regalloc.possibly_free_var(t)
        regalloc.possibly_free_var(t1)
        return fcond

    def emit_op_debug_merge_point(self, op, regalloc, fcond):
        return fcond
    emit_op_jit_debug = emit_op_debug_merge_point

class FieldOpAssembler(object):

    _mixin_ = True

    def emit_op_setfield_gc(self, op, regalloc, fcond):
        boxes = list(op.getarglist())
        a0, a1 = boxes
        ofs, size, ptr = self._unpack_fielddescr(op.getdescr())
        #ofs_loc = regalloc.make_sure_var_in_reg(ConstInt(ofs))
        #size_loc = regalloc.make_sure_var_in_reg(ofs)
        base_loc, base_box = self._ensure_value_is_boxed(a0, regalloc, boxes)
        boxes.append(base_box)
        value_loc, value_box = self._ensure_value_is_boxed(a1, regalloc, boxes)
        boxes.append(value_box)
        regalloc.possibly_free_vars(boxes)
        if size == 4:
            self.mc.STR_ri(value_loc.value, base_loc.value, ofs)
        elif size == 2:
            self.mc.STRH_ri(value_loc.value, base_loc.value, ofs)
        elif size == 1:
            self.mc.STRB_ri(value_loc.value, base_loc.value, ofs)
        else:
            assert 0
        return fcond

    emit_op_setfield_raw = emit_op_setfield_gc

    def emit_op_getfield_gc(self, op, regalloc, fcond):
        a0 = op.getarg(0)
        ofs, size, ptr = self._unpack_fielddescr(op.getdescr())
        # ofs_loc = regalloc.make_sure_var_in_reg(ConstInt(ofs))
        base_loc, base_box = self._ensure_value_is_boxed(a0, regalloc)
        res = regalloc.force_allocate_reg(op.result, [a0])
        regalloc.possibly_free_var(a0)
        regalloc.possibly_free_var(base_box)
        regalloc.possibly_free_var(op.result)

        if size == 4:
            self.mc.LDR_ri(res.value, base_loc.value, ofs)
        elif size == 2:
            self.mc.LDRH_ri(res.value, base_loc.value, ofs)
        elif size == 1:
            self.mc.LDRB_ri(res.value, base_loc.value, ofs)
        else:
            assert 0

        #XXX Hack, Hack, Hack
        if not we_are_translated():
            signed = op.getdescr().is_field_signed()
            self._ensure_result_bit_extension(res, size, signed, regalloc)
        return fcond

    emit_op_getfield_raw = emit_op_getfield_gc
    emit_op_getfield_raw_pure = emit_op_getfield_gc
    emit_op_getfield_gc_pure = emit_op_getfield_gc



    #XXX from ../x86/regalloc.py:791
    def _unpack_fielddescr(self, fielddescr):
        assert isinstance(fielddescr, BaseFieldDescr)
        ofs = fielddescr.offset
        size = fielddescr.get_field_size(self.cpu.translate_support_code)
        ptr = fielddescr.is_pointer_field()
        return ofs, size, ptr

class ArrayOpAssember(object):

    _mixin_ = True

    def emit_op_arraylen_gc(self, op, regalloc, fcond):
        arraydescr = op.getdescr()
        assert isinstance(arraydescr, BaseArrayDescr)
        ofs = arraydescr.get_ofs_length(self.cpu.translate_support_code)
        arg = op.getarg(0)
        base_loc, base_box = self._ensure_value_is_boxed(arg, regalloc)
        res = regalloc.force_allocate_reg(op.result, forbidden_vars=[arg, base_box])
        regalloc.possibly_free_vars([arg, base_box, op.result])

        self.mc.LDR_ri(res.value, base_loc.value, ofs)
        return fcond

    def emit_op_setarrayitem_gc(self, op, regalloc, fcond):
        a0, a1, a2 = boxes = list(op.getarglist())
        _, scale, ofs, _, ptr = self._unpack_arraydescr(op.getdescr())

        base_loc, base_box  = self._ensure_value_is_boxed(a0, regalloc, boxes)
        boxes.append(base_box)
        ofs_loc, ofs_box = self._ensure_value_is_boxed(a1, regalloc, boxes)
        boxes.append(ofs_box)
        #XXX check if imm would be fine here
        value_loc, value_box = self._ensure_value_is_boxed(a2, regalloc, boxes)
        boxes.append(value_box)
        regalloc.possibly_free_vars(boxes)

        if scale > 0:
            self.mc.LSL_ri(r.ip.value, ofs_loc.value, scale)
        else:
            self.mc.MOV_rr(r.ip.value, ofs_loc.value)

        if ofs > 0:
            self.mc.ADD_ri(r.ip.value, r.ip.value, ofs)

        if scale == 2:
            self.mc.STR_rr(value_loc.value, base_loc.value, r.ip.value, cond=fcond)
        elif scale == 1:
            self.mc.STRH_rr(value_loc.value, base_loc.value, r.ip.value, cond=fcond)
        elif scale == 0:
            self.mc.STRB_rr(value_loc.value, base_loc.value, r.ip.value, cond=fcond)
        else:
            assert 0
        return fcond

    emit_op_setarrayitem_raw = emit_op_setarrayitem_gc

    def emit_op_getarrayitem_gc(self, op, regalloc, fcond):
        a0, a1 = boxes = list(op.getarglist())
        _, scale, ofs, _, ptr = self._unpack_arraydescr(op.getdescr())

        base_loc, base_box  = self._ensure_value_is_boxed(a0, regalloc, boxes)
        boxes.append(base_box)
        ofs_loc, ofs_box = self._ensure_value_is_boxed(a1, regalloc, boxes)
        boxes.append(ofs_box)
        res = regalloc.force_allocate_reg(op.result)
        regalloc.possibly_free_vars(boxes)
        regalloc.possibly_free_var(op.result)

        if scale > 0:
            self.mc.LSL_ri(r.ip.value, ofs_loc.value, scale)
        else:
            self.mc.MOV_rr(r.ip.value, ofs_loc.value)
        if ofs > 0:
            self.mc.ADD_ri(r.ip.value, r.ip.value, imm=ofs)

        if scale == 2:
            self.mc.LDR_rr(res.value, base_loc.value, r.ip.value, cond=fcond)
        elif scale == 1:
            self.mc.LDRH_rr(res.value, base_loc.value, r.ip.value, cond=fcond)
        elif scale == 0:
            self.mc.LDRB_rr(res.value, base_loc.value, r.ip.value, cond=fcond)
        else:
            assert 0

        #XXX Hack, Hack, Hack
        if not we_are_translated():
            descr = op.getdescr()
            size =  descr.get_item_size(False)
            signed = descr.is_item_signed()
            self._ensure_result_bit_extension(res, size, signed, regalloc)
        return fcond

    emit_op_getarrayitem_raw = emit_op_getarrayitem_gc
    emit_op_getarrayitem_gc_pure = emit_op_getarrayitem_gc

    #XXX from ../x86/regalloc.py:779
    def _unpack_arraydescr(self, arraydescr):
        assert isinstance(arraydescr, BaseArrayDescr)
        ofs_length = arraydescr.get_ofs_length(self.cpu.translate_support_code)
        ofs = arraydescr.get_base_size(self.cpu.translate_support_code)
        size = arraydescr.get_item_size(self.cpu.translate_support_code)
        ptr = arraydescr.is_array_of_pointers()
        scale = 0
        while (1 << scale) < size:
            scale += 1
        assert (1 << scale) == size
        return size, scale, ofs, ofs_length, ptr

class StrOpAssembler(object):

    _mixin_ = True

    def emit_op_strlen(self, op, regalloc, fcond):
        l0, box = self._ensure_value_is_boxed(op.getarg(0), regalloc)
        boxes = [box]

        res = regalloc.force_allocate_reg(op.result, boxes)
        boxes.append(op.result)

        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                             self.cpu.translate_support_code)
        ofs_box = ConstInt(ofs_length)
        imm_ofs = self._check_imm_arg(ofs_box)

        if imm_ofs:
            l1 = regalloc.make_sure_var_in_reg(ofs_box, boxes)
        else:
            l1, box1 = self._ensure_value_is_boxed(ofs_box, regalloc, boxes)
            boxes.append(box1)

        regalloc.possibly_free_vars(boxes)

        if l1.is_imm():
            self.mc.LDR_ri(res.value, l0.value, l1.getint(), cond=fcond)
        else:
            self.mc.LDR_rr(res.value, l0.value, l1.value, cond=fcond)
        return fcond

    def emit_op_strgetitem(self, op, regalloc, fcond):
        boxes = list(op.getarglist())
        base_loc, box = self._ensure_value_is_boxed(boxes[0], regalloc)
        boxes.append(box)

        a1 = boxes[1]
        imm_a1 = self._check_imm_arg(a1)
        if imm_a1:
            ofs_loc = regalloc.make_sure_var_in_reg(a1, boxes)
        else:
            ofs_loc, box = self._ensure_value_is_boxed(a1, regalloc, boxes)
            boxes.append(box)
        res = regalloc.force_allocate_reg(op.result)
        regalloc.possibly_free_vars(boxes)

        regalloc.possibly_free_var(op.result)

        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                             self.cpu.translate_support_code)
        assert itemsize == 1
        if ofs_loc.is_imm():
            self.mc.ADD_ri(r.ip.value, base_loc.value, ofs_loc.getint(), cond=fcond)
        else:
            self.mc.ADD_rr(r.ip.value, base_loc.value, ofs_loc.value, cond=fcond)

        self.mc.LDRB_ri(res.value, r.ip.value, basesize, cond=fcond)
        return fcond

    def emit_op_strsetitem(self, op, regalloc, fcond):
        boxes = list(op.getarglist())

        base_loc, box = self._ensure_value_is_boxed(boxes[0], regalloc, boxes)
        boxes.append(box)

        ofs_loc, box = self._ensure_value_is_boxed(boxes[1], regalloc, boxes)
        boxes.append(box)

        value_loc, box = self._ensure_value_is_boxed(boxes[2], regalloc, boxes)
        boxes.append(box)

        regalloc.possibly_free_vars(boxes)

        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                             self.cpu.translate_support_code)
        assert itemsize == 1
        if ofs_loc.is_imm():
            self.mc.ADD_ri(r.ip.value, base_loc.value, ofs_loc.getint(), cond=fcond)
        else:
            self.mc.ADD_rr(r.ip.value, base_loc.value, ofs_loc.value, cond=fcond)

        self.mc.STRB_ri(value_loc.value, r.ip.value, basesize, cond=fcond)
        return fcond

    #from ../x86/regalloc.py:928 ff.
    def emit_op_copystrcontent(self, op, regalloc, fcond):
        self._emit_copystrcontent(op, regalloc, fcond, is_unicode=False)
        return fcond

    def emit_op_copyunicodecontent(self, op, regalloc, fcond):
        self._emit_copystrcontent(op, regalloc, fcond, is_unicode=True)
        return fcond

    def _emit_copystrcontent(self, op, regalloc, fcond, is_unicode):
        # compute the source address
        args = list(op.getarglist())
        base_loc, box = self._ensure_value_is_boxed(args[0], regalloc, args)
        args.append(box)
        ofs_loc, box = self._ensure_value_is_boxed(args[2], regalloc, args)
        args.append(box)
        assert args[0] is not args[1]    # forbidden case of aliasing
        regalloc.possibly_free_var(args[0])
        if args[3] is not args[2] is not args[4]:  # MESS MESS MESS: don't free
            regalloc.possibly_free_var(args[2])     # it if ==args[3] or args[4]
        srcaddr_box = TempBox()
        forbidden_vars = [args[1], args[3], args[4], srcaddr_box]
        srcaddr_loc = regalloc.force_allocate_reg(srcaddr_box,
                                    forbidden_vars, selected_reg=r.r1)
        self._gen_address_inside_string(base_loc, ofs_loc, srcaddr_loc,
                                        is_unicode=is_unicode)

        # compute the destination address
        forbidden_vars = [args[4], args[3], srcaddr_box]
        dstaddr_box = TempBox()
        dstaddr_loc = regalloc.force_allocate_reg(dstaddr_box, selected_reg=r.r0)
        forbidden_vars.append(dstaddr_box)
        base_loc, box = self._ensure_value_is_boxed(args[1], regalloc, forbidden_vars)
        args.append(box)
        forbidden_vars.append(box)
        ofs_loc, box = self._ensure_value_is_boxed(args[3], regalloc, forbidden_vars)
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
        length_loc, length_box = self._ensure_value_is_boxed(args[4], regalloc, forbidden_vars)
        args.append(length_box)
        if is_unicode:
            forbidden_vars = [srcaddr_box, dstaddr_box]
            bytes_box = TempBox()
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

    def emit_op_unicodelen(self, op, regalloc, fcond):
        l0, box = self._ensure_value_is_boxed(op.getarg(0), regalloc)
        boxes = [box]
        res = regalloc.force_allocate_reg(op.result, boxes)
        boxes.append(op.result)
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                             self.cpu.translate_support_code)
        ofs_box = ConstInt(ofs_length)
        imm_ofs = self._check_imm_arg(ofs_box)

        if imm_ofs:
            l1 = regalloc.make_sure_var_in_reg(ofs_box, boxes)
        else:
            l1, box1 = self._ensure_value_is_boxed(ofs_box, regalloc, boxes)
            boxes.append(box1)
        regalloc.possibly_free_vars(boxes)

        # XXX merge with strlen
        if l1.is_imm():
            self.mc.LDR_ri(res.value, l0.value, l1.getint(), cond=fcond)
        else:
            self.mc.LDR_rr(res.value, l0.value, l1.value, cond=fcond)
        return fcond

    def emit_op_unicodegetitem(self, op, regalloc, fcond):
        boxes = list(op.getarglist())

        base_loc, box = self._ensure_value_is_boxed(boxes[0], regalloc, boxes)
        boxes.append(box)

        ofs_loc, box = self._ensure_value_is_boxed(boxes[1], regalloc, boxes)
        boxes.append(box)

        res = regalloc.force_allocate_reg(op.result)

        regalloc.possibly_free_vars(boxes)
        regalloc.possibly_free_var(op.result)

        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                             self.cpu.translate_support_code)
        scale = itemsize/2

        self.mc.ADD_rr(r.ip.value, base_loc.value, ofs_loc.value, cond=fcond,
                                                imm=scale, shifttype=shift.LSL)
        if scale == 2:
            self.mc.LDR_ri(res.value, r.ip.value, basesize, cond=fcond)
        elif scale == 1:
            self.mc.LDRH_ri(res.value, r.ip.value, basesize, cond=fcond)
        else:
            assert 0, itemsize
        return fcond

    def emit_op_unicodesetitem(self, op, regalloc, fcond):
        boxes = list(op.getarglist())

        base_loc, box = self._ensure_value_is_boxed(boxes[0], regalloc, boxes)
        boxes.append(box)

        ofs_loc, box = self._ensure_value_is_boxed(boxes[1], regalloc, boxes)
        boxes.append(box)

        value_loc, box = self._ensure_value_is_boxed(boxes[2], regalloc, boxes)
        boxes.append(box)

        regalloc.possibly_free_vars(boxes)

        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                             self.cpu.translate_support_code)
        scale = itemsize/2

        self.mc.ADD_rr(r.ip.value, base_loc.value, ofs_loc.value, cond=fcond,
                                            imm=scale, shifttype=shift.LSL)
        if scale == 2:
            self.mc.STR_ri(value_loc.value, r.ip.value, basesize, cond=fcond)
        elif scale == 1:
            self.mc.STRH_ri(value_loc.value, r.ip.value, basesize, cond=fcond)
        else:
            assert 0, itemsize

        return fcond

class ForceOpAssembler(object):

    _mixin_ = True

    def emit_op_force_token(self, op, regalloc, fcond):
        res_loc = regalloc.force_allocate_reg(op.result)
        self.mc.MOV_rr(res_loc.value, r.fp.value)
        return fcond

    # from: ../x86/assembler.py:1668
    # XXX Split into some helper methods
    def emit_guard_call_assembler(self, op, guard_op, regalloc, fcond):
        faildescr = guard_op.getdescr()
        fail_index = self.cpu.get_fail_descr_number(faildescr)
        self._write_fail_index(fail_index, regalloc)

        descr = op.getdescr()
        assert isinstance(descr, LoopToken)

        resbox = TempBox()
        self._emit_call(descr._arm_direct_bootstrap_code, op.getarglist(),
                                                regalloc, fcond, result=resbox)
        #self.mc.ensure_bytes_available(256)
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
        assert value <= 0xff

        # check value
        t = TempBox()
        #XXX is this correct?
        resloc = regalloc.force_allocate_reg(resbox)
        loc = regalloc.force_allocate_reg(t)
        self.mc.gen_load_int(loc.value, value)
        self.mc.CMP_rr(resloc.value, loc.value)
        regalloc.possibly_free_var(resbox)

        fast_jmp_pos = self.mc.currpos()
        fast_jmp_location = self.mc.curraddr()
        self.mc.NOP()

        #if values are equal we take the fast pat
        # Slow path, calling helper
        # jump to merge point
        jd = descr.outermost_jitdriver_sd
        assert jd is not None
        asm_helper_adr = self.cpu.cast_adr_to_int(jd.assembler_helper_adr)
        self._emit_call(asm_helper_adr, [t, op.getarg(0)], regalloc, fcond, False, op.result)
        regalloc.possibly_free_var(t)

        # jump to merge point
        jmp_pos = self.mc.currpos()
        jmp_location = self.mc.curraddr()
        self.mc.NOP()

        # Fast Path using result boxes
        # patch the jump to the fast path
        offset = self.mc.currpos() - fast_jmp_pos
        pmc = ARMv7InMemoryBuilder(fast_jmp_location, WORD)
        pmc.ADD_ri(r.pc.value, r.pc.value, offset - PC_OFFSET, cond=c.EQ)

        # Reset the vable token --- XXX really too much special logic here:-(
        # XXX Enable and fix this once the stange errors procuded by its
        # presence are fixed
        #if jd.index_of_virtualizable >= 0:
        #    from pypy.jit.backend.llsupport.descr import BaseFieldDescr
        #    size = jd.portal_calldescr.get_result_size(self.cpu.translate_support_code)
        #    vable_index = jd.index_of_virtualizable
        #    regalloc._sync_var(op.getarg(vable_index))
        #    vable = regalloc.frame_manager.loc(op.getarg(vable_index))
        #    fielddescr = jd.vable_token_descr
        #    assert isinstance(fielddescr, BaseFieldDescr)
        #    ofs = fielddescr.offset
        #    self.mc.MOV(eax, arglocs[1])
        #    self.mc.MOV_mi((eax.value, ofs), 0)
        #    # in the line above, TOKEN_NONE = 0

        if op.result is not None:
            # load the return value from fail_boxes_xxx[0]
            loc = regalloc.force_allocate_reg(t)
            resloc = regalloc.force_allocate_reg(op.result, [t])
            kind = op.result.type
            if kind == INT:
                adr = self.fail_boxes_int.get_addr_for_num(0)
            elif kind == REF:
                adr = self.fail_boxes_ptr.get_addr_for_num(0)
            else:
                raise AssertionError(kind)
            self.mc.gen_load_int(loc.value, adr)
            self.mc.LDR_ri(resloc.value, loc.value)
            regalloc.possibly_free_var(t)

        offset = self.mc.currpos() - jmp_pos
        pmc = ARMv7InMemoryBuilder(jmp_location, WORD)
        pmc.ADD_ri(r.pc.value, r.pc.value, offset - PC_OFFSET)

        l0 = regalloc.force_allocate_reg(t)
        self.mc.LDR_ri(l0.value, r.fp.value)
        self.mc.CMP_ri(l0.value, 0)
        regalloc.possibly_free_var(t)
        regalloc.possibly_free_vars_for_op(op)
        if op.result:
            regalloc.possibly_free_var(op.result)

        self._emit_guard(guard_op, regalloc, c.GE)
        return fcond

    def emit_guard_call_may_force(self, op, guard_op, regalloc, fcond):
        faildescr = guard_op.getdescr()
        fail_index = self.cpu.get_fail_descr_number(faildescr)
        self._write_fail_index(fail_index, regalloc)

        # force all reg values to be spilled when calling
        fcond = self.emit_op_call(op, regalloc, fcond, save_all_regs=True)

        t = TempBox()
        l0 = regalloc.force_allocate_reg(t)
        self.mc.LDR_ri(l0.value, r.fp.value)
        self.mc.CMP_ri(l0.value, 0)
        regalloc.possibly_free_var(t)

        self._emit_guard(guard_op, regalloc, c.GE)
        return fcond

    def _write_fail_index(self, fail_index, regalloc):
        t = TempBox()
        l0 = regalloc.force_allocate_reg(t)
        self.mc.gen_load_int(l0.value, fail_index)
        self.mc.STR_ri(l0.value, r.fp.value)
        regalloc.possibly_free_var(t)

class AllocOpAssembler(object):

    _mixin_ = True

    def _prepare_args_for_new_op(self, new_args, regalloc):
        gc_ll_descr = self.cpu.gc_ll_descr
        args = gc_ll_descr.args_for_new(new_args)
        arglocs = []
        for arg in args:
            t = TempBox()
            l = regalloc.force_allocate_reg(t, arglocs)
            self.mc.gen_load_int(l.value, arg)
            arglocs.append(t)
        return arglocs

    # from: ../x86/regalloc.py:750
    # XXX kill this function at some point
    def _malloc_varsize(self, ofs_items, ofs_length, itemsize, v, res_v, regalloc):
        boxes = [v, res_v]
        itemsize_box = ConstInt(itemsize)
        ofs_items_box = ConstInt(ofs_items)
        if self._check_imm_arg(ofs_items_box):
            ofs_items_loc = regalloc.convert_to_imm(ofs_items_box)
        else:
            ofs_items_loc, ofs_items_box = self._ensure_value_is_boxed(ofs_items_box, regalloc, boxes)
            boxes.append(ofs_items_box)
        vloc, v = self._ensure_value_is_boxed(v, regalloc, [res_v])
        boxes.append(v)
        size, size_box = self._ensure_value_is_boxed(itemsize_box, regalloc, boxes)

        self.mc.MUL(size.value, size.value, vloc.value)
        if ofs_items_loc.is_imm():
            self.mc.ADD_ri(size.value, size.value, ofs_items_loc.value)
        else:
            self.mc.ADD_rr(size.value, size.value, ofs_items_loc.value)
        self._emit_call(self.malloc_func_addr, [size_box], regalloc, result=res_v)

        base_loc = regalloc.make_sure_var_in_reg(res_v)
        value_loc = regalloc.make_sure_var_in_reg(v)
        self.mc.STR_ri(value_loc.value, base_loc.value, ofs_length)

        regalloc.possibly_free_vars(boxes)

    def emit_op_new(self, op, regalloc, fcond):
        arglocs = self._prepare_args_for_new_op(op.getdescr(), regalloc)
        self._emit_call(self.malloc_func_addr, arglocs,
                                regalloc, result=op.result)
        regalloc.possibly_free_vars(arglocs)
        regalloc.possibly_free_var(op.result)
        return fcond

    def emit_op_new_with_vtable(self, op, regalloc, fcond):
        classint = op.getarg(0).getint()
        descrsize = heaptracker.vtable2descr(self.cpu, classint)
        arglocs = self._prepare_args_for_new_op(descrsize, regalloc)
        self._emit_call(self.malloc_func_addr, arglocs,
                                regalloc, result=op.result)
        resloc = regalloc.loc(op.result) # r0
        self.set_vtable(resloc, classint, regalloc)
        regalloc.possibly_free_vars(arglocs)
        regalloc.possibly_free_var(op.result)
        return fcond

    def set_vtable(self, loc, vtable, regalloc):
        if self.cpu.vtable_offset is not None:
            assert loc.is_reg()
            adr = rffi.cast(lltype.Signed, vtable)
            t = TempBox()
            loc_vtable = regalloc.force_allocate_reg(t)
            regalloc.possibly_free_var(t)
            self.mc.gen_load_int(loc_vtable.value, adr)
            self.mc.STR_ri(loc_vtable.value, loc.value, self.cpu.vtable_offset)

    def emit_op_new_array(self, op, regalloc, fcond):
        gc_ll_descr = self.cpu.gc_ll_descr
        if gc_ll_descr.get_funcptr_for_newarray is not None:
            raise NotImplementedError
            #XXX make sure this path works
            # framework GC
            #args = self.cpu.gc_ll_descr.args_for_new_array(op.getdescr())
            #arglocs = [imm(x) for x in args]
            #arglocs.append(self.loc(op.getarg(0)))
            #return self._emit_call(self.malloc_array_func_addr, op.getarglist(),
            #                        regalloc, result=op.result)
        # boehm GC (XXX kill the following code at some point)
        itemsize, scale, basesize, ofs_length, _ = (
            self._unpack_arraydescr(op.getdescr()))
        self._malloc_varsize(basesize, ofs_length, itemsize,
                                    op.getarg(0), op.result, regalloc)
        return fcond


    def emit_op_newstr(self, op, regalloc, fcond):
        gc_ll_descr = self.cpu.gc_ll_descr
        if gc_ll_descr.get_funcptr_for_newstr is not None:
            raise NotImplementedError
            # framework GC
            #loc = self.loc(op.getarg(0))
            #return self._call(op, [loc])
        # boehm GC (XXX kill the following code at some point)
        ofs_items, itemsize, ofs = symbolic.get_array_token(rstr.STR,
                                            self.cpu.translate_support_code)
        assert itemsize == 1
        self._malloc_varsize(ofs_items, ofs, itemsize, op.getarg(0),
                                                        op.result, regalloc)
        return fcond



    def emit_op_newunicode(self, op, regalloc, fcond):
        gc_ll_descr = self.cpu.gc_ll_descr
        if gc_ll_descr.get_funcptr_for_newunicode is not None:
            raise NotImplementedError
            # framework GC
            #loc = self.loc(op.getarg(0))
            #return self._call(op, [loc])
        # boehm GC (XXX kill the following code at some point)
        ofs_items, _, ofs = symbolic.get_array_token(rstr.UNICODE,
                                               self.cpu.translate_support_code)
        _, itemsize, _ = symbolic.get_array_token(rstr.UNICODE,
                                                  self.cpu.translate_support_code)
        self._malloc_varsize(ofs_items, ofs, itemsize, op.getarg(0),
                                                op.result, regalloc)
        return fcond

class ResOpAssembler(GuardOpAssembler, IntOpAsslember,
                    OpAssembler, UnaryIntOpAssembler,
                    FieldOpAssembler, ArrayOpAssember,
                    StrOpAssembler, UnicodeOpAssembler,
                    ForceOpAssembler, AllocOpAssembler):
    pass


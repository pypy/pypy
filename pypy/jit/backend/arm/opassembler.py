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
                                        BasicFailDescr, LoopToken, INT, REF)
from pypy.jit.metainterp.resoperation import rop
from pypy.rlib import rgc
from pypy.rlib.objectmodel import we_are_translated
from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.lltypesystem import lltype, rffi, rstr, llmemory

class IntOpAsslember(object):

    _mixin_ = True

    def emit_op_int_add(self, op, regalloc, fcond):
        # assuming only one argument is constant
        a0 = op.getarg(0)
        a1 = op.getarg(1)
        imm_a0 = isinstance(a0, ConstInt) and (a0.getint() <= 0xFF or -1 * a0.getint() <= 0xFF)
        imm_a1 = isinstance(a1, ConstInt) and (a1.getint() <= 0xFF or -1 * a1.getint() <= 0xFF)
        if imm_a0:
            imm_a0, imm_a1 = imm_a1, imm_a0
            a0, a1 = a1, a0
        if imm_a1:
            l0 = regalloc.make_sure_var_in_reg(a0, imm_fine=False)
            l1 = regalloc.make_sure_var_in_reg(a1, [a0], imm_fine=True)
            res = regalloc.force_allocate_reg(op.result, [a0, a1])
            if l1.getint() < 0:
                self.mc.SUB_ri(res.value, l0.value, -1 * l1.getint(), s=1)
            else:
                self.mc.ADD_ri(res.value, l0.value, l1.getint(), s=1)
        else:
            l0 = regalloc.make_sure_var_in_reg(a0, imm_fine=False)
            l1 = regalloc.make_sure_var_in_reg(a1, forbidden_vars=[a0], imm_fine=False)
            res = regalloc.force_allocate_reg(op.result, forbidden_vars=[a0, a1])
            self.mc.ADD_rr(res.value, l0.value, l1.value, s=1)

        regalloc.possibly_free_var(a0)
        regalloc.possibly_free_var(a1)
        regalloc.possibly_free_var(op.result)
        return fcond

    def emit_op_int_sub(self, op, regalloc, fcond):
        # assuming only one argument is constant
        a0 = op.getarg(0)
        a1 = op.getarg(1)
        imm_a0 = isinstance(a0, ConstInt) and (a0.getint() <= 0xFF or -1 * a0.getint() <= 0xFF)
        imm_a1 = isinstance(a1, ConstInt) and (a1.getint() <= 0xFF or -1 * a1.getint() <= 0xFF)
        l0 = regalloc.make_sure_var_in_reg(a0, imm_fine=imm_a0)
        l1 = regalloc.make_sure_var_in_reg(a1, [a0], imm_fine=imm_a1)
        res = regalloc.force_allocate_reg(op.result, [a0, a1])
        if imm_a0:
            value = l0.getint()
            if value < 0:
                # XXX needs a test
                self.mc.ADD_ri(res.value, l1.value, -1 * value, s=1)
                self.mc.MVN_rr(res.value, l1.value, s=1)
            else:
                # reverse substract ftw
                self.mc.RSB_ri(res.value, l1.value, value, s=1)
        elif imm_a1:
            value = l1.getint()
            if value < 0:
                self.mc.ADD_ri(res.value, l0.value, -1 * value, s=1)
            else:
                self.mc.SUB_ri(res.value, l0.value, value, s=1)
        else:
            self.mc.SUB_rr(res.value, l0.value, l1.value, s=1)

        regalloc.possibly_free_var(a0)
        regalloc.possibly_free_var(a1)
        regalloc.possibly_free_var(op.result)
        return fcond

    def emit_op_int_mul(self, op, regalloc, fcond):
        a0 = op.getarg(0)
        a1 = op.getarg(1)
        reg1 = regalloc.make_sure_var_in_reg(a0, [a1], imm_fine=False)
        reg2 = regalloc.make_sure_var_in_reg(a1, [a0], imm_fine=False)
        res = regalloc.force_allocate_reg(op.result, [a0, a1])
        self.mc.MUL(res.value, reg1.value, reg2.value)
        regalloc.possibly_free_vars_for_op(op)
        regalloc.possibly_free_var(op.result)
        return fcond

    #ref: http://blogs.arm.com/software-enablement/detecting-overflow-from-mul/
    def emit_guard_int_mul_ovf(self, op, guard, regalloc, fcond):
        a0 = op.getarg(0)
        a1 = op.getarg(1)
        reg1 = regalloc.make_sure_var_in_reg(a0, [a1], imm_fine=False)
        reg2 = regalloc.make_sure_var_in_reg(a1, [a0], imm_fine=False)
        res = regalloc.force_allocate_reg(op.result, [a0, a1])
        self.mc.SMULL(res.value, r.ip.value, reg1.value, reg2.value, cond=fcond)
        self.mc.CMP_rr(r.ip.value, res.value, shifttype=shift.ASR, imm=31, cond=fcond)
        regalloc.possibly_free_vars_for_op(op)
        if op.result:
            regalloc.possibly_free_var(op.result)
        if guard.getopnum() == rop.GUARD_OVERFLOW:
            return self._emit_guard(guard, regalloc, c.NE)
        else:
            return self._emit_guard(guard, regalloc, c.EQ)

    emit_op_int_floordiv = gen_emit_op_by_helper_call('DIV')
    emit_op_int_mod = gen_emit_op_by_helper_call('MOD')
    emit_op_uint_floordiv = gen_emit_op_by_helper_call('UDIV')

    emit_op_int_and = gen_emit_op_ri('AND')
    emit_op_int_or = gen_emit_op_ri('ORR')
    emit_op_int_xor = gen_emit_op_ri('EOR')
    emit_op_int_lshift = gen_emit_op_ri('LSL', imm_size=0x1F, allow_zero=False, commutative=False)
    emit_op_int_rshift = gen_emit_op_ri('ASR', imm_size=0x1F, commutative=False)
    emit_op_uint_rshift = gen_emit_op_ri('LSR', imm_size=0x1F, commutative=False)

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
        a0 = op.getarg(0)
        reg = regalloc.make_sure_var_in_reg(a0, imm_fine=False)
        res = regalloc.force_allocate_reg(op.result, [a0])

        self.mc.MVN_rr(res.value, reg.value)
        regalloc.possibly_free_vars_for_op(op)
        if op.result:
            regalloc.possibly_free_var(op.result)
        return fcond

    #XXX check for a better way of doing this
    def emit_op_int_neg(self, op, regalloc, fcond):
        arg = op.getarg(0)
        l0 = regalloc.make_sure_var_in_reg(arg, imm_fine=False)
        l1 = regalloc.make_sure_var_in_reg(ConstInt(-1), [arg], imm_fine=False)
        res = regalloc.force_allocate_reg(op.result, [arg])
        self.mc.MUL(res.value, l0.value, l1.value)
        regalloc.possibly_free_vars([l0, l1, res])
        return fcond

class GuardOpAssembler(object):

    _mixin_ = True

    guard_size = ARMv7Builder.size_of_gen_load_int + 6*WORD
    def _emit_guard(self, op, regalloc, fcond, save_exc=False):
        descr = op.getdescr()
        assert isinstance(descr, BasicFailDescr)
        #if hasattr(op, 'getfailargs'):
        #   print 'Failargs: ', op.getfailargs()

        self.mc.ensure_can_fit(self.guard_size)
        self.mc.ADD_ri(r.pc.value, r.pc.value, self.guard_size, cond=fcond)
        descr._arm_guard_code = self.mc.curraddr()

        self.mc.PUSH([reg.value for reg in r.caller_resp])
        addr = self.cpu.get_on_leave_jitted_int(save_exception=save_exc)
        self.mc.BL(addr)
        self.mc.POP([reg.value for reg in r.caller_resp])

        memaddr = self._gen_path_to_exit_path(op, op.getfailargs(), regalloc)
        descr._failure_recovery_code = memaddr
        regalloc.possibly_free_vars_for_op(op)
        self.mc.NOP()
        return c.AL

    def emit_op_guard_true(self, op, regalloc, fcond):
        a0 = op.getarg(0)
        l0 = regalloc.make_sure_var_in_reg(a0, imm_fine=False)
        self.mc.CMP_ri(l0.value, 0)
        regalloc.possibly_free_var(l0)
        return self._emit_guard(op, regalloc, c.NE)

    def emit_op_guard_false(self, op, regalloc, fcond):
        a0 = op.getarg(0)
        l0 = regalloc.make_sure_var_in_reg(a0, imm_fine=False)
        self.mc.CMP_ri(l0.value, 0)
        regalloc.possibly_free_var(l0)
        return self._emit_guard(op, regalloc, c.EQ)

    def emit_op_guard_value(self, op, regalloc, fcond):
        a0 = op.getarg(0)
        a1 = op.getarg(1)
        imm_a1 = self._check_imm_arg(a1)
        l0 = regalloc.make_sure_var_in_reg(a0, imm_fine=False)
        l1 = regalloc.make_sure_var_in_reg(a1, imm_fine=imm_a1)
        if l1.is_imm():
            self.mc.CMP_ri(l0.value, l1.getint())
        else:
            self.mc.CMP_rr(l0.value, l1.value)
        regalloc.possibly_free_vars_for_op(op)
        return self._emit_guard(op, regalloc, c.EQ)

    emit_op_guard_nonnull = emit_op_guard_true
    emit_op_guard_isnull = emit_op_guard_false

    def emit_op_guard_no_overflow(self, op, regalloc, fcond):
        return self._emit_guard(op, regalloc, c.VC)

    def emit_op_guard_overflow(self, op, regalloc, fcond):
        return self._emit_guard(op, regalloc, c.VS)

    # from ../x86/assembler.py:1265
    def emit_op_guard_class(self, op, regalloc, fcond):
        locs, boxes = self._prepare_guard_class(op, regalloc, fcond)
        self._cmp_guard_class(op, locs, regalloc, fcond)
        regalloc.possibly_free_vars(boxes)
        return fcond

    def emit_op_guard_nonnull_class(self, op, regalloc, fcond):
        locs, boxes = self._prepare_guard_class(op, regalloc, fcond)
        self.mc.CMP_ri(locs[0].value, 0)
        self._emit_guard(op, regalloc, c.NE)
        self._cmp_guard_class(op, locs, regalloc, fcond)
        regalloc.possibly_free_vars(boxes)
        return fcond

    def _prepare_guard_class(self, op, regalloc, fcond):
        assert isinstance(op.getarg(0), Box)

        x = regalloc.make_sure_var_in_reg(op.getarg(0), imm_fine=False)
        y_temp = TempBox()
        y = regalloc.force_allocate_reg(y_temp)
        self.mc.gen_load_int(y.value,
                        self.cpu.cast_adr_to_int(op.getarg(1).getint()))
        return [x, y], [op.getarg(0), y_temp]


    def _cmp_guard_class(self, op, locs, regalloc, fcond):
        offset = self.cpu.vtable_offset
        x = locs[0]
        y = locs[1]
        if offset is not None:
            t0 = TempBox()
            l0 = regalloc.force_allocate_reg(t0)
            assert offset == 0
            self.mc.LDR_ri(l0.value, x.value, offset)
            self.mc.CMP_rr(l0.value, y.value)
            regalloc.possibly_free_var(t0)
        else:
            raise NotImplentedError
            # XXX port from x86 backend once gc support is in place

        regalloc.possibly_free_vars_for_op(op)
        return self._emit_guard(op, regalloc, c.EQ)



class OpAssembler(object):

    _mixin_ = True

    def emit_op_jump(self, op, regalloc, fcond):
        destlocs = op.getdescr()._arm_arglocs
        srclocs  = [regalloc.loc(op.getarg(i)) for i in range(op.numargs())]
        remap_frame_layout(self, srclocs, destlocs, r.ip)

        loop_code = op.getdescr()._arm_loop_code
        self.mc.B(loop_code, fcond)
        return fcond

    def emit_op_finish(self, op, regalloc, fcond):
        self._gen_path_to_exit_path(op, op.getarglist(), regalloc, c.AL)
        return fcond

    def emit_op_call(self, op, regalloc, fcond, save_all_regs=False):
        adr = self.cpu.cast_adr_to_int(op.getarg(0).getint())
        args = op.getarglist()[1:]
        cond =  self._emit_call(adr, args, regalloc, fcond, save_all_regs, op.result)

        descr = op.getdescr()
        #XXX Hack, Hack, Hack
        if op.result and not we_are_translated() and not isinstance(descr, LoopToken):
            loc = regalloc.loc(op.result)
            size = descr.get_result_size(False)
            signed = descr.is_result_signed()
            self._ensure_result_bit_extension(loc, size, signed, regalloc)
        return cond

    def _emit_call(self, adr, args, regalloc, fcond=c.AL, save_all_regs=False, result=None):
        locs = []
        # all arguments past the 4th go on the stack
        # XXX support types other than int (one word types)
        n = 0
        n_args = len(args)
        if n_args > 4:
            stack_args = n_args - 4
            n = stack_args*WORD
            self._adjust_sp(n, regalloc, fcond=fcond)
            for i in range(4, n_args):
                reg = regalloc.make_sure_var_in_reg(args[i])
                self.mc.STR_ri(reg.value, r.sp.value, (i-4)*WORD)
                regalloc.possibly_free_var(reg)


        reg_args = min(n_args, 4)
        for i in range(0, reg_args):
            l = regalloc.make_sure_var_in_reg(args[i],
                                            selected_reg=r.all_regs[i])
            locs.append(l)
        # XXX use PUSH here instead of spilling every reg for itself
        if save_all_regs:
            regalloc.before_call(r.all_regs, save_all_regs)
        else:
            regalloc.before_call()
        self.mc.BL(adr)

        if result:
            regalloc.after_call(result)
        # readjust the sp in case we passed some args on the stack
        if n_args > 4:
            assert n > 0
            self._adjust_sp(-n, regalloc, fcond=fcond)
        regalloc.possibly_free_vars(args)
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
        self._emit_guard(op, regalloc, c.EQ, save_exc=True)
        regalloc.possibly_free_var(t)

    def emit_op_guard_exception(self, op, regalloc, fcond):
        args = op.getarglist()
        t = TempBox()
        t1 = TempBox()
        loc = regalloc.force_allocate_reg(t, args)
        loc1 = regalloc.force_allocate_reg(t1, args + [t])
        self.mc.gen_load_int(loc.value,
            self.cpu.cast_adr_to_int(
                op.getarg(0).getint()), fcond)

        self.mc.gen_load_int(loc1.value, self.cpu.pos_exception(), fcond)
        self.mc.LDR_ri(loc1.value, loc1.value)

        self.mc.CMP_rr(loc1.value, loc.value)
        self._emit_guard(op, regalloc, c.EQ, save_exc=True)
        self.mc.gen_load_int(loc1.value, self.cpu.pos_exc_value(), fcond)
        if op.result in regalloc.longevity:
            resloc = regalloc.force_allocate_reg(op.result, args + [t, t1])
            self.mc.LDR_ri(resloc.value, loc1.value)
            regalloc.possibly_free_var(resloc)
        self.mc.gen_load_int(loc.value, self.cpu.pos_exception(), fcond)
        self.mc.MOV_ri(r.ip.value, 0)
        self.mc.STR_ri(r.ip.value, loc.value)
        self.mc.STR_ri(r.ip.value, loc1.value)
        regalloc.possibly_free_var(t)
        regalloc.possibly_free_var(t1)
        return fcond

class FieldOpAssembler(object):

    _mixin_ = True

    def emit_op_setfield_gc(self, op, regalloc, fcond):
        a0 = op.getarg(0)
        a1 = op.getarg(1)
        ofs, size, ptr = self._unpack_fielddescr(op.getdescr())
        #ofs_loc = regalloc.make_sure_var_in_reg(ConstInt(ofs))
        #size_loc = regalloc.make_sure_var_in_reg(ofs)
        base_loc = regalloc.make_sure_var_in_reg(a0, imm_fine=False)
        value_loc = regalloc.make_sure_var_in_reg(a1, [a0], imm_fine=False)
        if size == 4:
            f = self.mc.STR_ri
        elif size == 2:
            f = self.mc.STRH_ri
        elif size == 1:
            f = self.mc.STRB_ri
        else:
            assert 0
        f(value_loc.value, base_loc.value, ofs)
        return fcond

    emit_op_setfield_raw = emit_op_setfield_gc

    def emit_op_getfield_gc(self, op, regalloc, fcond):
        a0 = op.getarg(0)
        ofs, size, ptr = self._unpack_fielddescr(op.getdescr())
        # ofs_loc = regalloc.make_sure_var_in_reg(ConstInt(ofs))
        base_loc = regalloc.make_sure_var_in_reg(a0, imm_fine=False)
        res = regalloc.force_allocate_reg(op.result, [a0])
        if size == 4:
            f = self.mc.LDR_ri
        elif size == 2:
            f = self.mc.LDRH_ri
        elif size == 1:
            f = self.mc.LDRB_ri
        else:
            assert 0
        f(res.value, base_loc.value, ofs)

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
        base_loc = regalloc.make_sure_var_in_reg(op.getarg(0), imm_fine=False)
        regalloc.possibly_free_vars_for_op(op)
        res = regalloc.force_allocate_reg(op.result, forbidden_vars=[base_loc])

        self.mc.LDR_ri(res.value, base_loc.value, ofs)
        regalloc.possibly_free_var(op.getarg(0))
        if op.result:
            regalloc.possibly_free_var(op.result)

    def emit_op_setarrayitem_gc(self, op, regalloc, fcond):
        a0 = op.getarg(0)
        a1 = op.getarg(1)
        a2 = op.getarg(2)
        _, scale, ofs, _, ptr = self._unpack_arraydescr(op.getdescr())

        base_loc  = regalloc.make_sure_var_in_reg(a0, imm_fine=False)
        ofs_loc = regalloc.make_sure_var_in_reg(a1, imm_fine=False)
        #XXX check if imm would be fine here
        value_loc = regalloc.make_sure_var_in_reg(a2, imm_fine=False)

        if scale > 0:
            self.mc.LSL_ri(ofs_loc.value, ofs_loc.value, scale)
        if ofs > 0:
            self.mc.ADD_ri(ofs_loc.value, ofs_loc.value, ofs)

        if scale == 2:
            self.mc.STR_rr(value_loc.value, base_loc.value, ofs_loc.value, cond=fcond)
        elif scale == 1:
            self.mc.STRH_rr(value_loc.value, base_loc.value, ofs_loc.value, cond=fcond)
        elif scale == 0:
            self.mc.STRB_rr(value_loc.value, base_loc.value, ofs_loc.value, cond=fcond)
        else:
            assert 0
        return fcond

    emit_op_setarrayitem_raw = emit_op_setarrayitem_gc

    def emit_op_getarrayitem_gc(self, op, regalloc, fcond):
        a0 = op.getarg(0)
        a1 = op.getarg(1)
        _, scale, ofs, _, ptr = self._unpack_arraydescr(op.getdescr())

        base_loc  = regalloc.make_sure_var_in_reg(a0, imm_fine=False)
        ofs_loc = regalloc.make_sure_var_in_reg(a1, imm_fine=False)
        res = regalloc.force_allocate_reg(op.result)

        if scale > 0:
            self.mc.LSL_ri(ofs_loc.value, ofs_loc.value, scale)
        if ofs > 0:
            self.mc.ADD_ri(ofs_loc.value, ofs_loc.value, imm=ofs)

        if scale == 2:
            f = self.mc.LDR_rr
        elif scale == 1:
            f = self.mc.LDRH_rr
        elif scale == 0:
            f = self.mc.LDRB_rr
        else:
            assert 0

        f(res.value, base_loc.value, ofs_loc.value, cond=fcond)
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
        l0 = regalloc.make_sure_var_in_reg(op.getarg(0), imm_fine=False)
        regalloc.possibly_free_vars_for_op(op)
        res = regalloc.force_allocate_reg(op.result)
        if op.result:
            regalloc.possibly_free_var(op.result)
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                             self.cpu.translate_support_code)
        l1 = regalloc.make_sure_var_in_reg(ConstInt(ofs_length))
        if l1.is_imm():
            self.mc.LDR_ri(res.value, l0.value, l1.getint(), cond=fcond)
        else:
            self.mc.LDR_rr(res.value, l0.value, l1.value, cond=fcond)
        return fcond

    def emit_op_strgetitem(self, op, regalloc, fcond):
        base_loc = regalloc.make_sure_var_in_reg(op.getarg(0), imm_fine=False)
        ofs_loc = regalloc.make_sure_var_in_reg(op.getarg(1))
        t = TempBox()
        temp = regalloc.force_allocate_reg(t)
        res = regalloc.force_allocate_reg(op.result)
        regalloc.possibly_free_vars_for_op(op)
        regalloc.possibly_free_var(t)
        regalloc.possibly_free_var(op.result)

        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                             self.cpu.translate_support_code)
        assert itemsize == 1
        if ofs_loc.is_imm():
            self.mc.ADD_ri(temp.value, base_loc.value, ofs_loc.getint(), cond=fcond)
        else:
            self.mc.ADD_rr(temp.value, base_loc.value, ofs_loc.value, cond=fcond)

        self.mc.LDRB_ri(res.value, temp.value, basesize, cond=fcond)
        return fcond

    def emit_op_strsetitem(self, op, regalloc, fcond):
        base_loc = regalloc.make_sure_var_in_reg(op.getarg(0), imm_fine=False)
        ofs_loc = regalloc.make_sure_var_in_reg(op.getarg(1))
        value_loc = regalloc.make_sure_var_in_reg(op.getarg(2))
        t = TempBox()
        temp = regalloc.force_allocate_reg(t)
        regalloc.possibly_free_vars_for_op(op)
        regalloc.possibly_free_var(t)
        if op.result:
            regalloc.possibly_free_var(op.result)

        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                             self.cpu.translate_support_code)
        assert itemsize == 1
        if ofs_loc.is_imm():
            self.mc.ADD_ri(temp.value, base_loc.value, ofs_loc.getint(), cond=fcond)
        else:
            self.mc.ADD_rr(temp.value, base_loc.value, ofs_loc.value, cond=fcond)

        self.mc.STRB_ri(value_loc.value, temp.value, basesize, cond=fcond)
        return fcond
    #from ../x86/regalloc.py:928 ff.
    def emit_op_copystrcontent(self, op, regalloc, fcond):
        self._emit_copystrcontent(op, regalloc, fcond, is_unicode=False)

    def emit_op_copyunicodecontent(self, op, regalloc, fcond):
        self._emit_copystrcontent(op, regalloc, fcond, is_unicode=True)

    def _emit_copystrcontent(self, op, regalloc, fcond, is_unicode):
        # compute the source address
        args = op.getarglist()
        boxes = []
        base_loc, box = self._ensure_value_is_boxed(args[0], regalloc)
        boxes.append(box)
        ofs_loc, box = self._ensure_value_is_boxed(args[2], regalloc)
        boxes.append(box)
        assert args[0] is not args[1]    # forbidden case of aliasing

        srcaddr_box = TempBox()
        forbidden_vars = [args[1], args[3], args[4], srcaddr_box]
        srcaddr_loc = regalloc.force_allocate_reg(srcaddr_box, forbidden_vars)
        self._gen_address_inside_string(base_loc, ofs_loc, srcaddr_loc,
                                        is_unicode=is_unicode)
        regalloc.possibly_free_var(boxes[0])
        if args[3] is not args[2] is not args[4]:  # MESS MESS MESS: don't free
            regalloc.possibly_free_var(boxes[1])     # it if ==args[3] or args[4]

        # compute the destination address
        base_loc, box = self._ensure_value_is_boxed(args[1], regalloc)
        boxes.append(box)
        ofs_loc, box = self._ensure_value_is_boxed(args[3], regalloc)
        boxes.append(box)
        assert base_loc.is_reg()
        assert ofs_loc.is_reg()
        forbidden_vars = [args[4], srcaddr_box]
        dstaddr_box = TempBox()
        dstaddr_loc = regalloc.force_allocate_reg(dstaddr_box,
                                forbidden_vars)
        self._gen_address_inside_string(base_loc, ofs_loc, dstaddr_loc,
                                        is_unicode=is_unicode)
        regalloc.possibly_free_var(boxes[2])
        if args[3] is not args[4]:     # more of the MESS described above
            regalloc.possibly_free_var(boxes[3])

        # compute the length in bytes
        length_loc, length_box = self._ensure_value_is_boxed(args[4], regalloc)
        boxes.append(length_box)
        if is_unicode:
            forbidden_vars = [srcaddr_box, dstaddr_box]
            bytes_box = TempBox()
            bytes_loc = regalloc.force_allocate_reg(bytes_box, forbidden_vars)
            scale = self._get_unicode_item_scale()
            self.mc.MOV_rr(bytes_loc.value, length_loc.value)
            self._load_address(length_loc, 0, scale, bytes_loc)
            length_box = bytes_box
            length_loc = bytes_loc
        # call memcpy()
        self._emit_call(self.memcpy_addr, [dstaddr_box, srcaddr_box, length_box], regalloc)

        regalloc.possibly_free_var(length_box)
        regalloc.possibly_free_var(dstaddr_box)
        regalloc.possibly_free_var(srcaddr_box)
        regalloc.possibly_free_vars_for_op(op)
        regalloc.possibly_free_vars(boxes)

    def _load_address(self, sizereg, baseofs, scale, result, baseloc=None):
        if baseloc is not None:
            assert baseloc.is_reg()
            self.mc.MOV_rr(result.value, baseloc.value)
        else:
            self.mc.MOV_ri(result.value, 0)
        assert sizereg.is_reg()
        if scale > 0:
            self.mc.LSL_ri(r.ip.value, sizereg.value, scale)
        else:
            self.mc.MOV_rr(r.ip.value, sizereg.value)
        self.mc.ADD_rr(result.value, result.value, r.ip.value)
        self.mc.ADD_ri(result.value, result.value, baseofs)

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
        self._load_address(ofsloc, ofs_items, scale, resloc, baseloc)

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
        l0 = regalloc.make_sure_var_in_reg(op.getarg(0), imm_fine=False)
        regalloc.possibly_free_vars_for_op(op)
        res = regalloc.force_allocate_reg(op.result)
        regalloc.possibly_free_var(op.result)
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                             self.cpu.translate_support_code)
        l1 = regalloc.make_sure_var_in_reg(ConstInt(ofs_length))
        if l1.is_imm():
            self.mc.LDR_ri(res.value, l0.value, l1.getint(), cond=fcond)
        else:
            self.mc.LDR_rr(res.value, l0.value, l1.value, cond=fcond)
        return fcond

    def emit_op_unicodegetitem(self, op, regalloc, fcond):
        base_loc = regalloc.make_sure_var_in_reg(op.getarg(0), imm_fine=False)
        ofs_loc = regalloc.make_sure_var_in_reg(op.getarg(1), imm_fine=False)
        t = TempBox()
        temp = regalloc.force_allocate_reg(t)
        res = regalloc.force_allocate_reg(op.result)
        regalloc.possibly_free_vars_for_op(op)
        regalloc.possibly_free_var(t)
        if op.result:
            regalloc.possibly_free_var(op.result)

        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                             self.cpu.translate_support_code)
        scale = itemsize/2
        if scale == 2:
            f = self.mc.LDR_ri
        elif scale == 1:
            f = self.mc.LDRH_ri
        else:
            assert 0, itemsize
        self.mc.ADD_rr(temp.value, base_loc.value, ofs_loc.value, cond=fcond,
                                                imm=scale, shifttype=shift.LSL)
        f(res.value, temp.value, basesize, cond=fcond)
        return fcond

    def emit_op_unicodesetitem(self, op, regalloc, fcond):
        base_loc = regalloc.make_sure_var_in_reg(op.getarg(0), imm_fine=False)
        ofs_loc = regalloc.make_sure_var_in_reg(op.getarg(1))
        value_loc = regalloc.make_sure_var_in_reg(op.getarg(2))
        t = TempBox()
        temp = regalloc.force_allocate_reg(t)
        regalloc.possibly_free_vars_for_op(op)
        regalloc.possibly_free_var(t)
        if op.result:
            regalloc.possibly_free_var(op.result)

        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                             self.cpu.translate_support_code)
        scale = itemsize/2
        if scale == 2:
            f = self.mc.STR_ri
        elif scale == 1:
            f = self.mc.STRH_ri
        else:
            assert 0, itemsize

        self.mc.ADD_rr(temp.value, base_loc.value, ofs_loc.value, cond=fcond,
                                            imm=scale, shifttype=shift.LSL)
        f(value_loc.value, temp.value, basesize, cond=fcond)
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
        resloc = regalloc.force_allocate_reg(resbox)
        loc = regalloc.force_allocate_reg(t, [r.r0])
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
            l = regalloc.force_allocate_reg(t)
            self.mc.gen_load_int(l.value, arg)
            arglocs.append(t)
        return arglocs

    # from: ../x86/regalloc.py:750
    # XXX kill this function at some point
    def _malloc_varsize(self, ofs_items, ofs_length, scale, v, res_v, regalloc):
        tempbox = TempBox()
        size_loc = regalloc.force_allocate_reg(tempbox)
        self.mc.gen_load_int(size_loc.value, ofs_items + (v.getint() << scale))
        self._emit_call(self.malloc_func_addr, [tempbox],
                                regalloc, result=res_v)
        loc = regalloc.make_sure_var_in_reg(v, [res_v])
        regalloc.possibly_free_var(v)
        if tempbox is not None:
            regalloc.possibly_free_var(tempbox)

        # XXX combine with emit_op_setfield_gc operation
        base_loc = regalloc.loc(res_v)
        value_loc = regalloc.loc(v)
        size = scale * 2
        ofs = ofs_length
        if size == 4:
            f = self.mc.STR_ri
        elif size == 2:
            f = self.mc.STRH_ri
        elif size == 1:
            f = self.mc.STRB_ri
        else:
            assert 0
        f(value_loc.value, base_loc.value, ofs)

    def emit_op_new(self, op, regalloc, fcond):
        arglocs = self._prepare_args_for_new_op(op.getdescr(), regalloc)
        self._emit_call(self.malloc_func_addr, arglocs,
                                regalloc, result=op.result)
        regalloc.possibly_free_vars(arglocs)
        return fcond

    def emit_op_new_with_vtable(self, op, regalloc, fcond):
        classint = op.getarg(0).getint()
        descrsize = heaptracker.vtable2descr(self.cpu, classint)
        arglocs = self._prepare_args_for_new_op(descrsize, regalloc)
        self._emit_call(self.malloc_func_addr, arglocs,
                                regalloc, result=op.result)
        regalloc.possibly_free_vars(arglocs)
        self.set_vtable(op.result, op.getarg(0), regalloc)
        return fcond

    def set_vtable(self, result, vtable, regalloc):
        loc = regalloc.loc(result)
        if self.cpu.vtable_offset is not None:
            assert loc.is_reg()
            adr = self.cpu.cast_adr_to_int(vtable.getint())
            t = TempBox()
            loc_vtable = regalloc.force_allocate_reg(t)
            self.mc.gen_load_int(loc_vtable.value, adr)
            #assert isinstance(loc_vtable, ImmedLoc)
            self.mc.STR_ri(loc_vtable.value, loc.value, self.cpu.vtable_offset)
            regalloc.possibly_free_var(t)

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
        return self._malloc_varsize(basesize, ofs_length, scale,
                                    op.getarg(0), op.result, regalloc)


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
        return self._malloc_varsize(ofs_items, ofs, 1, op.getarg(0),
                                                        op.result, regalloc)



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
        scale = self._get_unicode_item_scale()
        return self._malloc_varsize(ofs_items, ofs, scale, op.getarg(0),
                                                op.result, regalloc)

    def _get_unicode_item_scale(self):
        _, itemsize, _ = symbolic.get_array_token(rstr.UNICODE,
                                                  self.cpu.translate_support_code)
        if itemsize == 4:
            return 2
        elif itemsize == 2:
            return 1
        else:
            raise AssertionError("bad unicode item size")

class ResOpAssembler(GuardOpAssembler, IntOpAsslember,
                    OpAssembler, UnaryIntOpAssembler,
                    FieldOpAssembler, ArrayOpAssember,
                    StrOpAssembler, UnicodeOpAssembler,
                    ForceOpAssembler, AllocOpAssembler):
    pass


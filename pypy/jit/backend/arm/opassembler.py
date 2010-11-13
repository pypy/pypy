from pypy.jit.backend.arm import conditions as c
from pypy.jit.backend.arm import locations
from pypy.jit.backend.arm import registers as r
from pypy.jit.backend.arm import shift
from pypy.jit.backend.arm.arch import (WORD, FUNC_ALIGN, arm_int_div,
                                        arm_int_div_sign, arm_int_mod_sign, arm_int_mod)

from pypy.jit.backend.arm.helper.assembler import (gen_emit_op_by_helper_call,
                                                    gen_emit_op_unary_cmp,
                                                    gen_emit_op_ri, gen_emit_cmp_op)
from pypy.jit.backend.arm.codebuilder import ARMv7Builder, ARMv7InMemoryBuilder
from pypy.jit.backend.arm.regalloc import ARMRegisterManager
from pypy.jit.backend.llsupport import symbolic
from pypy.jit.backend.llsupport.descr import BaseFieldDescr, BaseArrayDescr
from pypy.jit.backend.llsupport.regalloc import compute_vars_longevity, TempBox
from pypy.jit.metainterp.history import ConstInt, BoxInt, BasicFailDescr
from pypy.jit.metainterp.resoperation import rop
from pypy.rlib import rgc
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

        regalloc.possibly_free_vars_for_op(op)
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

        regalloc.possibly_free_vars_for_op(op)
        return fcond

    def emit_op_int_mul(self, op, regalloc, fcond):
        a0 = op.getarg(0)
        a1 = op.getarg(1)
        reg1 = regalloc.make_sure_var_in_reg(a0, imm_fine=False)
        reg2 = regalloc.make_sure_var_in_reg(a1, [a0], imm_fine=False)
        res = regalloc.force_allocate_reg(op.result, [a0, a1])
        self.mc.MUL(res.value, reg1.value, reg2.value)
        regalloc.possibly_free_vars_for_op(op)
        return fcond

    #ref: http://blogs.arm.com/software-enablement/detecting-overflow-from-mul/
    def emit_op_int_mul_ovf(self, op, regalloc, fcond):
        a0 = op.getarg(0)
        a1 = op.getarg(1)
        reg1 = regalloc.make_sure_var_in_reg(a0, imm_fine=False)
        reg2 = regalloc.make_sure_var_in_reg(a1, [a0], imm_fine=False)
        res = regalloc.force_allocate_reg(op.result, [a0, a1])
        self.mc.SMULL(res.value, r.ip.value, reg1.value, reg2.value, cond=fcond)
        self.mc.CMP_rr(r.ip.value, res.value, shifttype=shift.ASR, imm=31, cond=fcond)
        regalloc.possibly_free_vars_for_op(op)
        return 0xF # XXX Remove: hack to show that the prev operation was  a mul_ovf

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

    def _emit_guard(self, op, regalloc, fcond):
        descr = op.getdescr()
        assert isinstance(descr, BasicFailDescr)
        descr._arm_guard_code = self.mc.curraddr()
        memaddr = self._gen_path_to_exit_path(op, op.getfailargs(), regalloc, fcond)
        descr._failure_recovery_code = memaddr
        descr._arm_guard_cond = fcond
        descr._arm_guard_size = self.mc.curraddr() - descr._arm_guard_code
        regalloc.possibly_free_vars_for_op(op)
        return c.AL

    def emit_op_guard_true(self, op, regalloc, fcond):
        a0 = op.getarg(0)
        l0 = regalloc.make_sure_var_in_reg(a0, imm_fine=False)
        self.mc.CMP_ri(l0.value, 0)
        regalloc.possibly_free_var(l0)
        return self._emit_guard(op, regalloc, c.EQ)

    def emit_op_guard_false(self, op, regalloc, fcond):
        a0 = op.getarg(0)
        l0 = regalloc.make_sure_var_in_reg(a0, imm_fine=False)
        self.mc.CMP_ri(l0.value, 0)
        regalloc.possibly_free_var(l0)
        return self._emit_guard(op, regalloc, c.NE)

    def emit_op_guard_value(self, op, regalloc, fcond):
        a0 = op.getarg(0)
        a1 = op.getarg(1)
        l0 = regalloc.make_sure_var_in_reg(a0, imm_fine=False)
        l1 = regalloc.make_sure_var_in_reg(a1)
        if l1.is_imm():
            self.mc.CMP_rr(l0.value, l1.getint())
        else:
            self.mc.CMP_rr(l0.value, l1.value)
        regalloc.possibly_free_vars_for_op(op)
        return self._emit_guard(op, regalloc, c.NE)

    emit_op_guard_nonnull = emit_op_guard_true
    emit_op_guard_isnull = emit_op_guard_false

    def emit_op_guard_no_overflow(self, op, regalloc, fcond):
        if fcond == 0xF: # XXX: hack to check if the prev op was a mul_ovf
            return self._emit_guard(op, regalloc, c.NE)
        return self._emit_guard(op, regalloc, c.VS)

    def emit_op_guard_overflow(self, op, regalloc, fcond):
        if fcond == 0xF: # XXX: hack to check if the prev op was a mul_ovf
            return self._emit_guard(op, regalloc, c.EQ)
        return self._emit_guard(op, regalloc, c.VC)

class OpAssembler(object):

    _mixin_ = True

    def emit_op_jump(self, op, regalloc, fcond):
        registers = op.getdescr()._arm_arglocs
        for i in range(op.numargs()):
            # avoid moving stuff twice
            loc = registers[i]
            prev_loc = regalloc.loc(op.getarg(i))
            self.mov_loc_loc(prev_loc, loc)

        loop_code = op.getdescr()._arm_loop_code
        self.mc.B(loop_code, fcond)
        return fcond

    def emit_op_finish(self, op, regalloc, fcond):
        self._gen_path_to_exit_path(op, op.getarglist(), regalloc, c.AL)
        return fcond

    def emit_op_call(self, op, regalloc, fcond, save_all_regs=False):
        locs = []
        # all arguments past the 4th go on the stack
        # XXX support types other than int (one word types)
        if op.numargs() > 5:
            stack_args = op.numargs() - 5
            n = stack_args*WORD
            self._adjust_sp(n, regalloc, fcond=fcond)
            for i in range(5, op.numargs()):
                reg = regalloc.make_sure_var_in_reg(op.getarg(i))
                self.mc.STR_ri(reg.value, r.sp.value, (i-5)*WORD)
                regalloc.possibly_free_var(reg)

        adr = self.cpu.cast_adr_to_int(op.getarg(0).getint())

        reg_args = min(op.numargs()-1, 4)
        for i in range(1, reg_args+1):
            l = regalloc.make_sure_var_in_reg(op.getarg(i),
                                            selected_reg=r.all_regs[i-1])
            locs.append(l)
        # XXX use PUSH here instead of spilling every reg for itself
        if save_all_regs:
            regalloc.before_call(r.all_regs, save_all_regs)
        else:
            regalloc.before_call()
        regalloc.force_allocate_reg(op.result, selected_reg=r.r0)
        self.mc.BL(adr)
        regalloc.after_call(op.result)
        # readjust the sp in case we passed some args on the stack
        if op.numargs() > 5:
            self._adjust_sp(-n, regalloc, fcond=fcond)
        regalloc.possibly_free_vars(locs)

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

    def emit_op_setarrayitem_gc(self, op, regalloc, fcond):
        a0 = op.getarg(0)
        a1 = op.getarg(1)
        a2 = op.getarg(2)
        scale, ofs, _, ptr = self._unpack_arraydescr(op.getdescr())

        base_loc  = regalloc.make_sure_var_in_reg(a0, imm_fine=False)
        ofs_loc = regalloc.make_sure_var_in_reg(a1, imm_fine=False)
        #XXX check if imm would be fine here
        value_loc = regalloc.make_sure_var_in_reg(a2, imm_fine=False)

        if scale == 2:
            self.mc.STR_rr(value_loc.value, base_loc.value, ofs_loc.value, cond=fcond,
                            imm=scale, shifttype=shift.LSL)
        elif scale == 1:
            self.mc.LSL_ri(ofs_loc.value, ofs_loc.value, scale)
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
        scale, ofs, _, ptr = self._unpack_arraydescr(op.getdescr())

        base_loc  = regalloc.make_sure_var_in_reg(a0, imm_fine=False)
        ofs_loc = regalloc.make_sure_var_in_reg(a1, imm_fine=False)
        res = regalloc.force_allocate_reg(op.result)
        if scale == 2:
            f = self.mc.LDR_rr
        elif scale == 1:
            f = self.mc.LDRH_rr
        elif scale == 0:
            f = self.mc.LDRB_rr
        else:
            assert 0
        if scale > 0:
            self.mc.LSL_ri(ofs_loc.value, ofs_loc.value, scale)
        f(res.value, base_loc.value, ofs_loc.value, cond=fcond)

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
        return scale, ofs, ofs_length, ptr

class StrOpAssembler(object):
    _mixin_ = True

    def emit_op_strlen(self, op, regalloc, fcond):
        l0 = regalloc.make_sure_var_in_reg(op.getarg(0), imm_fine=False)
        regalloc.possibly_free_vars_for_op(op)
        res = regalloc.force_allocate_reg(op.result)
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

        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                             self.cpu.translate_support_code)
        assert itemsize == 1
        if ofs_loc.is_imm():
            self.mc.ADD_ri(temp.value, base_loc.value, ofs_loc.getint(), cond=fcond)
        else:
            self.mc.ADD_rr(temp.value, base_loc.value, ofs_loc.value, cond=fcond)

        self.mc.STRB_ri(value_loc.value, temp.value, basesize, cond=fcond)
        return fcond

class UnicodeOpAssembler(object):
    _mixin_ = True

    def emit_op_unicodelen(self, op, regalloc, fcond):
        l0 = regalloc.make_sure_var_in_reg(op.getarg(0), imm_fine=False)
        regalloc.possibly_free_vars_for_op(op)
        res = regalloc.force_allocate_reg(op.result)
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
    def emit_op_force_token(self, op, regalloc, fcond):
        res_loc = regalloc.force_allocate_reg(op.result)
        self.mc.MOV_rr(res_loc.value, r.fp.value)
        return fcond

    def emit_guard_call_may_force(self, op, guard_op, regalloc, fcond):
        faildescr = guard_op.getdescr()
        fail_index = self.cpu.get_fail_descr_number(faildescr)
        t = TempBox()
        l0 = regalloc.force_allocate_reg(t)
        self.mc.gen_load_int(l0.value, fail_index)
        self.mc.STR_ri(l0.value, r.fp.value)

        # force all reg values to be spilled when calling
        fcond = self.emit_op_call(op, regalloc, fcond, save_all_regs=True)

        self.mc.LDR_ri(l0.value, r.fp.value)
        self.mc.CMP_ri(l0.value, 0)

        regalloc.possibly_free_var(t)

        self._emit_guard(guard_op, regalloc, c.LT)
        return fcond

class ResOpAssembler(GuardOpAssembler, IntOpAsslember,
                    OpAssembler, UnaryIntOpAssembler,
                    FieldOpAssembler, ArrayOpAssember,
                    StrOpAssembler, UnicodeOpAssembler,
                    ForceOpAssembler):
    pass


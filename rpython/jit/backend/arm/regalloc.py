from rpython.rtyper.annlowlevel import cast_instance_to_gcref
from rpython.rlib import rgc
from rpython.rlib.debug import debug_print, debug_start, debug_stop
from rpython.jit.backend.llsupport.regalloc import FrameManager, \
        RegisterManager, TempBox, compute_vars_longevity, BaseRegalloc, \
        get_scale
from rpython.jit.backend.arm import registers as r
from rpython.jit.backend.arm import locations
from rpython.jit.backend.arm.locations import imm, get_fp_offset
from rpython.jit.backend.arm.helper.regalloc import (prepare_op_by_helper_call,
                                                    prepare_op_unary_cmp,
                                                    prepare_op_ri,
                                                    prepare_cmp_op,
                                                    prepare_float_op,
                                                    check_imm_arg,
                                                    check_imm_box,
                                                    VMEM_imm_size,
                                                    default_imm_size,
                                                    )
from rpython.jit.backend.arm.jump import remap_frame_layout_mixed
from rpython.jit.backend.arm.arch import WORD, JITFRAME_FIXED_SIZE
from rpython.jit.codewriter import longlong
from rpython.jit.metainterp.history import (Const, ConstInt, ConstFloat,
                                            ConstPtr, BoxInt,
                                            Box, BoxPtr,
                                            INT, REF, FLOAT)
from rpython.jit.metainterp.history import TargetToken
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.backend.llsupport.descr import ArrayDescr
from rpython.jit.backend.llsupport.gcmap import allocate_gcmap
from rpython.jit.backend.llsupport import symbolic
from rpython.rtyper.lltypesystem import lltype, rffi, rstr, llmemory
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.jit.backend.llsupport.descr import unpack_arraydescr
from rpython.jit.backend.llsupport.descr import unpack_fielddescr
from rpython.jit.backend.llsupport.descr import unpack_interiorfielddescr
from rpython.rlib.rarithmetic import r_uint
from rpython.jit.backend.llsupport.descr import CallDescr


# xxx hack: set a default value for TargetToken._ll_loop_code.  If 0, we know
# that it is a LABEL that was not compiled yet.
TargetToken._ll_loop_code = 0

class TempInt(TempBox):
    type = INT

    def __repr__(self):
        return "<TempInt at %s>" % (id(self),)


class TempPtr(TempBox):
    type = REF

    def __repr__(self):
        return "<TempPtr at %s>" % (id(self),)


class TempFloat(TempBox):
    type = FLOAT

    def __repr__(self):
        return "<TempFloat at %s>" % (id(self),)



class ARMFrameManager(FrameManager):

    def __init__(self, base_ofs):
        FrameManager.__init__(self)
        self.base_ofs = base_ofs

    def frame_pos(self, i, box_type):
        return locations.StackLocation(i, get_fp_offset(self.base_ofs, i), box_type)

    @staticmethod
    def frame_size(type):
        if type == FLOAT:
            return  2
        return 1

    @staticmethod
    def get_loc_index(loc):
        assert loc.is_stack()
        return loc.position


def void(self, op, fcond):
    return []

class ARMRegisterManager(RegisterManager):
    def return_constant(self, v, forbidden_vars=[], selected_reg=None):
        self._check_type(v)
        if isinstance(v, Const):
            if isinstance(v, ConstPtr):
                tp = REF
            elif isinstance(v, ConstFloat):
                tp = FLOAT
            else:
                tp = INT
            loc = self.get_scratch_reg(tp,
                    self.temp_boxes + forbidden_vars,
                    selected_reg=selected_reg)
            immvalue = self.convert_to_imm(v)
            self.assembler.load(loc, immvalue)
            return loc
        else:
            return RegisterManager.return_constant(self, v,
                                    forbidden_vars, selected_reg)


class VFPRegisterManager(ARMRegisterManager):
    all_regs = r.all_vfp_regs
    box_types = [FLOAT]
    save_around_call_regs = r.all_vfp_regs

    def convert_to_imm(self, c):
        adr = self.assembler.datablockwrapper.malloc_aligned(8, 8)
        x = c.getfloatstorage()
        rffi.cast(rffi.CArrayPtr(longlong.FLOATSTORAGE), adr)[0] = x
        return locations.ConstFloatLoc(adr)

    def __init__(self, longevity, frame_manager=None, assembler=None):
        RegisterManager.__init__(self, longevity, frame_manager, assembler)

    def after_call(self, v):
        """ Adjust registers according to the result of the call,
        which is in variable v.
        """
        self._check_type(v)
        reg = self.force_allocate_reg(v, selected_reg=r.d0)
        return reg

    def get_scratch_reg(self, type=FLOAT, forbidden_vars=[], selected_reg=None):
        assert type == FLOAT  # for now
        box = TempFloat()
        self.temp_boxes.append(box)
        reg = self.force_allocate_reg(box, forbidden_vars=forbidden_vars,
                                                    selected_reg=selected_reg)
        return reg


class CoreRegisterManager(ARMRegisterManager):
    all_regs = r.all_regs
    box_types = None       # or a list of acceptable types
    no_lower_byte_regs = all_regs
    save_around_call_regs = r.caller_resp

    def __init__(self, longevity, frame_manager=None, assembler=None):
        RegisterManager.__init__(self, longevity, frame_manager, assembler)

    def call_result_location(self, v):
        return r.r0

    def convert_to_imm(self, c):
        if isinstance(c, ConstInt):
            val = rffi.cast(rffi.INT, c.value)
            return locations.ImmLocation(val)
        else:
            assert isinstance(c, ConstPtr)
            return locations.ImmLocation(rffi.cast(lltype.Signed, c.value))
        assert 0

    def get_scratch_reg(self, type=INT, forbidden_vars=[], selected_reg=None):
        assert type == INT or type == REF
        box = None
        if type == INT:
            box = TempInt()
        else:
            box = TempPtr()
        self.temp_boxes.append(box)
        reg = self.force_allocate_reg(box, forbidden_vars=forbidden_vars,
                                                    selected_reg=selected_reg)
        return reg

    def get_free_reg(self):
        free_regs = self.free_regs
        for i in range(len(free_regs) - 1, -1, -1):
            if free_regs[i] in self.save_around_call_regs:
                continue
            return free_regs[i]


class Regalloc(BaseRegalloc):

    def __init__(self, assembler=None):
        self.cpu = assembler.cpu
        self.assembler = assembler
        self.frame_manager = None
        self.jump_target_descr = None
        self.final_jump_op = None

    def loc(self, var):
        if var.type == FLOAT:
            return self.vfprm.loc(var)
        else:
            return self.rm.loc(var)

    def position(self):
        return self.rm.position

    def next_instruction(self):
        self.rm.next_instruction()
        self.vfprm.next_instruction()

    def _check_invariants(self):
        self.rm._check_invariants()
        self.vfprm._check_invariants()

    def stays_alive(self, v):
        if v.type == FLOAT:
            return self.vfprm.stays_alive(v)
        else:
            return self.rm.stays_alive(v)

    def call_result_location(self, v):
        if v.type == FLOAT:
            return self.vfprm.call_result_location(v)
        else:
            return self.rm.call_result_location(v)

    def after_call(self, v):
        if v.type == FLOAT:
            return self.vfprm.after_call(v)
        else:
            return self.rm.after_call(v)

    def force_allocate_reg(self, var, forbidden_vars=[], selected_reg=None,
                           need_lower_byte=False):
        if var.type == FLOAT:
            return self.vfprm.force_allocate_reg(var, forbidden_vars,
                                               selected_reg, need_lower_byte)
        else:
            return self.rm.force_allocate_reg(var, forbidden_vars,
                                              selected_reg, need_lower_byte)

    def try_allocate_reg(self, v, selected_reg=None, need_lower_byte=False):
        if v.type == FLOAT:
            return self.vfprm.try_allocate_reg(v, selected_reg,
                                                            need_lower_byte)
        else:
            return self.rm.try_allocate_reg(v, selected_reg, need_lower_byte)

    def possibly_free_var(self, var):
        if var.type == FLOAT:
            self.vfprm.possibly_free_var(var)
        else:
            self.rm.possibly_free_var(var)

    def possibly_free_vars_for_op(self, op):
        for i in range(op.numargs()):
            var = op.getarg(i)
            if var is not None:  # xxx kludgy
                self.possibly_free_var(var)

    def possibly_free_vars(self, vars):
        for var in vars:
            if var is not None:  # xxx kludgy
                self.possibly_free_var(var)

    def get_scratch_reg(self, type, forbidden_vars=[], selected_reg=None):
        if type == FLOAT:
            return self.vfprm.get_scratch_reg(type, forbidden_vars,
                                                                selected_reg)
        else:
            return self.rm.get_scratch_reg(type, forbidden_vars, selected_reg)

    def get_free_reg(self):
        return self.rm.get_free_reg()

    def free_temp_vars(self):
        self.rm.free_temp_vars()
        self.vfprm.free_temp_vars()

    def make_sure_var_in_reg(self, var, forbidden_vars=[],
                         selected_reg=None, need_lower_byte=False):
        if var.type == FLOAT:
            return self.vfprm.make_sure_var_in_reg(var, forbidden_vars,
                                        selected_reg, need_lower_byte)
        else:
            return self.rm.make_sure_var_in_reg(var, forbidden_vars,
                                        selected_reg, need_lower_byte)

    def convert_to_imm(self, value):
        if isinstance(value, ConstInt):
            return self.rm.convert_to_imm(value)
        else:
            assert isinstance(value, ConstFloat)
            return self.vfprm.convert_to_imm(value)

    def _prepare(self, inputargs, operations, allgcrefs):
        cpu = self.assembler.cpu
        self.fm = ARMFrameManager(cpu.get_baseofs_of_frame_field())
        self.frame_manager = self.fm
        operations = cpu.gc_ll_descr.rewrite_assembler(cpu, operations,
                                                       allgcrefs)
        # compute longevity of variables
        longevity, last_real_usage = compute_vars_longevity(inputargs, operations)
        self.longevity = longevity
        self.last_real_usage = last_real_usage
        fm = self.frame_manager
        asm = self.assembler
        self.vfprm = VFPRegisterManager(longevity, fm, asm)
        self.rm = CoreRegisterManager(longevity, fm, asm)
        return operations

    def prepare_loop(self, inputargs, operations, looptoken, allgcrefs):
        operations = self._prepare(inputargs, operations, allgcrefs)
        self._set_initial_bindings(inputargs, looptoken)
        self.possibly_free_vars(list(inputargs))
        return operations

    def prepare_bridge(self, inputargs, arglocs, operations, allgcrefs,
                       frame_info):
        operations = self._prepare(inputargs, operations, allgcrefs)
        self._update_bindings(arglocs, inputargs)
        return operations

    def get_final_frame_depth(self):
        return self.frame_manager.get_frame_depth()

    def _update_bindings(self, locs, inputargs):
        used = {}
        i = 0
        for loc in locs:
            if loc is None:
                loc = r.fp
            arg = inputargs[i]
            i += 1
            if loc.is_core_reg():
                self.rm.reg_bindings[arg] = loc
                used[loc] = None
            elif loc.is_vfp_reg():
                self.vfprm.reg_bindings[arg] = loc
                used[loc] = None
            else:
                assert loc.is_stack()
                self.frame_manager.bind(arg, loc)

        # XXX combine with x86 code and move to llsupport
        self.rm.free_regs = []
        for reg in self.rm.all_regs:
            if reg not in used:
                self.rm.free_regs.append(reg)
        self.vfprm.free_regs = []
        for reg in self.vfprm.all_regs:
            if reg not in used:
                self.vfprm.free_regs.append(reg)
        # note: we need to make a copy of inputargs because possibly_free_vars
        # is also used on op args, which is a non-resizable list
        self.possibly_free_vars(list(inputargs))
        self.fm.finish_binding()
        self._check_invariants()

    def get_gcmap(self, forbidden_regs=[], noregs=False):
        frame_depth = self.fm.get_frame_depth()
        gcmap = allocate_gcmap(self.assembler,
                        frame_depth, JITFRAME_FIXED_SIZE)
        for box, loc in self.rm.reg_bindings.iteritems():
            if loc in forbidden_regs:
                continue
            if box.type == REF and self.rm.is_still_alive(box):
                assert not noregs
                assert loc.is_core_reg()
                val = loc.value
                gcmap[val // WORD // 8] |= r_uint(1) << (val % (WORD * 8))
        for box, loc in self.fm.bindings.iteritems():
            if box.type == REF and self.rm.is_still_alive(box):
                assert loc.is_stack()
                val = loc.position + JITFRAME_FIXED_SIZE
                gcmap[val // WORD // 8] |= r_uint(1) << (val % (WORD * 8))
        return gcmap

    # ------------------------------------------------------------
    def perform_llong(self, op, args, fcond):
        return self.assembler.regalloc_emit_llong(op, args, fcond, self)

    def perform_math(self, op, args, fcond):
        return self.assembler.regalloc_emit_math(op, args, self, fcond)

    def force_spill_var(self, var):
        if var.type == FLOAT:
            self.vfprm.force_spill_var(var)
        else:
            self.rm.force_spill_var(var)

    def before_call(self, force_store=[], save_all_regs=False):
        self.rm.before_call(force_store, save_all_regs)
        self.vfprm.before_call(force_store, save_all_regs)

    def _sync_var(self, v):
        if v.type == FLOAT:
            self.vfprm._sync_var(v)
        else:
            self.rm._sync_var(v)

    def _prepare_op_int_add(self, op, fcond):
        boxes = op.getarglist()
        a0, a1 = boxes
        imm_a0 = check_imm_box(a0)
        imm_a1 = check_imm_box(a1)
        if not imm_a0 and imm_a1:
            l0 = self.make_sure_var_in_reg(a0, boxes)
            l1 = self.convert_to_imm(a1)
        elif imm_a0 and not imm_a1:
            l0 = self.convert_to_imm(a0)
            l1 = self.make_sure_var_in_reg(a1, boxes)
        else:
            l0 = self.make_sure_var_in_reg(a0, boxes)
            l1 = self.make_sure_var_in_reg(a1, boxes)
        return [l0, l1]

    def prepare_op_int_add(self, op, fcond):
        locs = self._prepare_op_int_add(op, fcond)
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op.result)
        return locs + [res]

    def _prepare_op_int_sub(self, op, fcond):
        a0, a1 = boxes = op.getarglist()
        imm_a0 = check_imm_box(a0)
        imm_a1 = check_imm_box(a1)
        if not imm_a0 and imm_a1:
            l0 = self.make_sure_var_in_reg(a0, boxes)
            l1 = self.convert_to_imm(a1)
        elif imm_a0 and not imm_a1:
            l0 = self.convert_to_imm(a0)
            l1 = self.make_sure_var_in_reg(a1, boxes)
        else:
            l0 = self.make_sure_var_in_reg(a0, boxes)
            l1 = self.make_sure_var_in_reg(a1, boxes)
        return [l0, l1]

    def prepare_op_int_sub(self, op, fcond):
        locs = self._prepare_op_int_sub(op, fcond)
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op.result)
        return locs + [res]

    def prepare_op_int_mul(self, op, fcond):
        boxes = op.getarglist()
        a0, a1 = boxes

        reg1 = self.make_sure_var_in_reg(a0, forbidden_vars=boxes)
        reg2 = self.make_sure_var_in_reg(a1, forbidden_vars=boxes)

        self.possibly_free_vars(boxes)
        self.possibly_free_vars_for_op(op)
        res = self.force_allocate_reg(op.result)
        self.possibly_free_var(op.result)
        return [reg1, reg2, res]

    def prepare_op_int_force_ge_zero(self, op, fcond):
        argloc = self.make_sure_var_in_reg(op.getarg(0))
        resloc = self.force_allocate_reg(op.result, [op.getarg(0)])
        return [argloc, resloc]

    def prepare_guard_int_mul_ovf(self, op, guard, fcond):
        boxes = op.getarglist()
        reg1 = self.make_sure_var_in_reg(boxes[0], forbidden_vars=boxes)
        reg2 = self.make_sure_var_in_reg(boxes[1], forbidden_vars=boxes)
        res = self.force_allocate_reg(op.result)
        return self._prepare_guard(guard, [reg1, reg2, res])

    def prepare_guard_int_add_ovf(self, op, guard, fcond):
        locs = self._prepare_op_int_add(op, fcond)
        res = self.force_allocate_reg(op.result)
        locs.append(res)
        return self._prepare_guard(guard, locs)

    def prepare_guard_int_sub_ovf(self, op, guard, fcond):
        locs = self._prepare_op_int_sub(op, fcond)
        res = self.force_allocate_reg(op.result)
        locs.append(res)
        return self._prepare_guard(guard, locs)

    prepare_op_int_floordiv = prepare_op_by_helper_call('int_floordiv')
    prepare_op_int_mod = prepare_op_by_helper_call('int_mod')
    prepare_op_uint_floordiv = prepare_op_by_helper_call('unit_floordiv')

    prepare_op_int_and = prepare_op_ri('int_and')
    prepare_op_int_or = prepare_op_ri('int_or')
    prepare_op_int_xor = prepare_op_ri('int_xor')
    prepare_op_int_lshift = prepare_op_ri('int_lshift', imm_size=0x1F,
                                        allow_zero=False, commutative=False)
    prepare_op_int_rshift = prepare_op_ri('int_rshift', imm_size=0x1F,
                                        allow_zero=False, commutative=False)
    prepare_op_uint_rshift = prepare_op_ri('uint_rshift', imm_size=0x1F,
                                        allow_zero=False, commutative=False)

    prepare_op_int_lt = prepare_cmp_op('int_lt')
    prepare_op_int_le = prepare_cmp_op('int_le')
    prepare_op_int_eq = prepare_cmp_op('int_eq')
    prepare_op_int_ne = prepare_cmp_op('int_ne')
    prepare_op_int_gt = prepare_cmp_op('int_gt')
    prepare_op_int_ge = prepare_cmp_op('int_ge')

    prepare_op_uint_le = prepare_cmp_op('uint_le')
    prepare_op_uint_gt = prepare_cmp_op('uint_gt')

    prepare_op_uint_lt = prepare_cmp_op('uint_lt')
    prepare_op_uint_ge = prepare_cmp_op('uint_ge')

    prepare_op_ptr_eq = prepare_op_instance_ptr_eq = prepare_op_int_eq
    prepare_op_ptr_ne = prepare_op_instance_ptr_ne = prepare_op_int_ne

    prepare_guard_int_lt = prepare_cmp_op('guard_int_lt')
    prepare_guard_int_le = prepare_cmp_op('guard_int_le')
    prepare_guard_int_eq = prepare_cmp_op('guard_int_eq')
    prepare_guard_int_ne = prepare_cmp_op('guard_int_ne')
    prepare_guard_int_gt = prepare_cmp_op('guard_int_gt')
    prepare_guard_int_ge = prepare_cmp_op('guard_int_ge')

    prepare_guard_uint_le = prepare_cmp_op('guard_uint_le')
    prepare_guard_uint_gt = prepare_cmp_op('guard_uint_gt')

    prepare_guard_uint_lt = prepare_cmp_op('guard_uint_lt')
    prepare_guard_uint_ge = prepare_cmp_op('guard_uint_ge')

    prepare_guard_ptr_eq = prepare_guard_instance_ptr_eq = prepare_guard_int_eq
    prepare_guard_ptr_ne = prepare_guard_instance_ptr_ne = prepare_guard_int_ne

    prepare_op_int_add_ovf = prepare_op_int_add
    prepare_op_int_sub_ovf = prepare_op_int_sub

    prepare_op_int_is_true = prepare_op_unary_cmp('int_is_true')
    prepare_op_int_is_zero = prepare_op_unary_cmp('int_is_zero')

    prepare_guard_int_is_true = prepare_op_unary_cmp('int_is_true')
    prepare_guard_int_is_zero = prepare_op_unary_cmp('int_is_zero')

    def prepare_op_int_neg(self, op, fcond):
        l0 = self.make_sure_var_in_reg(op.getarg(0))
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        resloc = self.force_allocate_reg(op.result)
        return [l0, resloc]

    prepare_op_int_invert = prepare_op_int_neg

    def prepare_op_call(self, op, fcond):
        effectinfo = op.getdescr().get_extra_info()
        if effectinfo is not None:
            oopspecindex = effectinfo.oopspecindex
            if oopspecindex in (EffectInfo.OS_LLONG_ADD,
                            EffectInfo.OS_LLONG_SUB,
                            EffectInfo.OS_LLONG_AND,
                            EffectInfo.OS_LLONG_OR,
                            EffectInfo.OS_LLONG_XOR):
                args = self._prepare_llong_binop_xx(op, fcond)
                self.perform_llong(op, args, fcond)
                return
            if oopspecindex == EffectInfo.OS_LLONG_TO_INT:
                args = self._prepare_llong_to_int(op, fcond)
                self.perform_llong(op, args, fcond)
                return
            if oopspecindex == EffectInfo.OS_MATH_SQRT:
                args = self.prepare_op_math_sqrt(op, fcond)
                self.perform_math(op, args, fcond)
                return
        return self._prepare_call(op)

    def _prepare_call(self, op, force_store=[], save_all_regs=False):
        args = [None] * (op.numargs() + 3)
        calldescr = op.getdescr()
        assert isinstance(calldescr, CallDescr)
        assert len(calldescr.arg_classes) == op.numargs() - 1

        for i in range(op.numargs()):
            args[i + 3] = self.loc(op.getarg(i))

        size = calldescr.get_result_size()
        sign = calldescr.is_result_signed()
        if sign:
            sign_loc = imm(1)
        else:
            sign_loc = imm(0)
        args[1] = imm(size)
        args[2] = sign_loc

        args[0] = self._call(op, args, force_store, save_all_regs)
        return args

    def _call(self, op, arglocs, force_store=[], save_all_regs=False):
        # spill variables that need to be saved around calls
        self.vfprm.before_call(save_all_regs=save_all_regs)
        if not save_all_regs:
            gcrootmap = self.assembler.cpu.gc_ll_descr.gcrootmap
            if gcrootmap and gcrootmap.is_shadow_stack:
                save_all_regs = 2
        self.rm.before_call(save_all_regs=save_all_regs)
        self.before_call_called = True
        resloc = None
        if op.result:
            resloc = self.after_call(op.result)
        return resloc

    def prepare_op_call_malloc_gc(self, op, fcond):
        return self._prepare_call(op)

    def _prepare_llong_binop_xx(self, op, fcond):
        # arg 0 is the address of the function
        loc0 = self.make_sure_var_in_reg(op.getarg(1))
        loc1 = self.make_sure_var_in_reg(op.getarg(2))
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.vfprm.force_allocate_reg(op.result)
        return [loc0, loc1, res]

    def _prepare_llong_to_int(self, op, fcond):
        loc0 = self.make_sure_var_in_reg(op.getarg(1))
        res = self.force_allocate_reg(op.result)
        return [loc0, res]

    def _prepare_guard(self, op, args=None):
        if args is None:
            args = []
        args.append(imm(self.frame_manager.get_frame_depth()))
        for arg in op.getfailargs():
            if arg:
                args.append(self.loc(arg))
            else:
                args.append(None)
        return args

    def prepare_op_finish(self, op, fcond):
        # the frame is in fp, but we have to point where in the frame is
        # the potential argument to FINISH
        descr = op.getdescr()
        fail_descr = cast_instance_to_gcref(descr)
        # we know it does not move, but well
        rgc._make_sure_does_not_move(fail_descr)
        fail_descr = rffi.cast(lltype.Signed, fail_descr)
        if op.numargs() == 1:
            loc = self.make_sure_var_in_reg(op.getarg(0))
            locs = [loc, imm(fail_descr)]
        else:
            locs = [imm(fail_descr)]
        return locs

    def prepare_op_guard_true(self, op, fcond):
        l0 = self.make_sure_var_in_reg(op.getarg(0))
        args = self._prepare_guard(op, [l0])
        return args

    prepare_op_guard_false = prepare_op_guard_true
    prepare_op_guard_nonnull = prepare_op_guard_true
    prepare_op_guard_isnull = prepare_op_guard_true

    def prepare_op_guard_value(self, op, fcond):
        boxes = op.getarglist()
        a0, a1 = boxes
        imm_a1 = check_imm_box(a1)
        l0 = self.make_sure_var_in_reg(a0, boxes)
        if not imm_a1:
            l1 = self.make_sure_var_in_reg(a1, boxes)
        else:
            l1 = self.convert_to_imm(a1)
        assert op.result is None
        arglocs = self._prepare_guard(op, [l0, l1])
        self.possibly_free_vars(op.getarglist())
        self.possibly_free_vars(op.getfailargs())
        return arglocs

    def prepare_op_guard_no_overflow(self, op, fcond):
        locs = self._prepare_guard(op)
        self.possibly_free_vars(op.getfailargs())
        return locs

    prepare_op_guard_overflow = prepare_op_guard_no_overflow
    prepare_op_guard_not_invalidated = prepare_op_guard_no_overflow

    def prepare_op_guard_exception(self, op, fcond):
        boxes = op.getarglist()
        arg0 = ConstInt(rffi.cast(lltype.Signed, op.getarg(0).getint()))
        loc = self.make_sure_var_in_reg(arg0)
        loc1 = self.get_scratch_reg(INT, boxes)
        if op.result in self.longevity:
            resloc = self.force_allocate_reg(op.result, boxes)
            self.possibly_free_var(op.result)
        else:
            resloc = None
        pos_exc_value = imm(self.cpu.pos_exc_value())
        pos_exception = imm(self.cpu.pos_exception())
        arglocs = self._prepare_guard(op,
                    [loc, loc1, resloc, pos_exc_value, pos_exception])
        return arglocs

    def prepare_op_guard_no_exception(self, op, fcond):
        loc = self.make_sure_var_in_reg(ConstInt(self.cpu.pos_exception()))
        arglocs = self._prepare_guard(op, [loc])
        return arglocs

    def prepare_op_guard_class(self, op, fcond):
        return self._prepare_guard_class(op, fcond)

    prepare_op_guard_nonnull_class = prepare_op_guard_class

    def _prepare_guard_class(self, op, fcond):
        assert isinstance(op.getarg(0), Box)
        boxes = op.getarglist()

        x = self.make_sure_var_in_reg(boxes[0], boxes)
        y_val = rffi.cast(lltype.Signed, op.getarg(1).getint())

        arglocs = [x, None, None]

        offset = self.cpu.vtable_offset
        if offset is not None:
            y = self.get_scratch_reg(INT, forbidden_vars=boxes)
            self.assembler.load(y, imm(y_val))

            assert check_imm_arg(offset)
            offset_loc = imm(offset)

            arglocs[1] = y
            arglocs[2] = offset_loc
        else:
            # XXX hard-coded assumption: to go from an object to its class
            # we use the following algorithm:
            #   - read the typeid from mem(locs[0]), i.e. at offset 0
            #   - keep the lower 16 bits read there
            #   - multiply by 4 and use it as an offset in type_info_group
            #   - add 16 bytes, to go past the TYPE_INFO structure
            classptr = y_val
            # here, we have to go back from 'classptr' to the value expected
            # from reading the 16 bits in the object header
            from rpython.memory.gctypelayout import GCData
            sizeof_ti = rffi.sizeof(GCData.TYPE_INFO)
            type_info_group = llop.gc_get_type_info_group(llmemory.Address)
            type_info_group = rffi.cast(lltype.Signed, type_info_group)
            expected_typeid = classptr - sizeof_ti - type_info_group
            expected_typeid >>= 2
            if check_imm_arg(expected_typeid):
                arglocs[1] = imm(expected_typeid)
            else:
                y = self.get_scratch_reg(INT, forbidden_vars=boxes)
                self.assembler.load(y, imm(expected_typeid))
                arglocs[1] = y

        return self._prepare_guard(op, arglocs)

        return arglocs

    def compute_hint_frame_locations(self, operations):
        # optimization only: fill in the 'hint_frame_locations' dictionary
        # of rm and xrm based on the JUMP at the end of the loop, by looking
        # at where we would like the boxes to be after the jump.
        return # XXX disabled for now
        op = operations[-1]
        if op.getopnum() != rop.JUMP:
            return
        self.final_jump_op = op
        descr = op.getdescr()
        assert isinstance(descr, TargetToken)
        if descr._ll_loop_code != 0:
            # if the target LABEL was already compiled, i.e. if it belongs
            # to some already-compiled piece of code
            self._compute_hint_frame_locations_from_descr(descr)
        #else:
        #   The loop ends in a JUMP going back to a LABEL in the same loop.
        #   We cannot fill 'hint_frame_locations' immediately, but we can
        #   wait until the corresponding prepare_op_label() to know where the
        #   we would like the boxes to be after the jump.

    def _compute_hint_frame_locations_from_descr(self, descr):
        return
        #arglocs = self.assembler.target_arglocs(descr)
        #jump_op = self.final_jump_op
        #assert len(arglocs) == jump_op.numargs()
        #for i in range(jump_op.numargs()):
        #    box = jump_op.getarg(i)
        #    if isinstance(box, Box):
        #        loc = arglocs[i]
        #        if loc is not None and loc.is_stack():
        #            self.frame_manager.hint_frame_locations[box] = loc

    def prepare_op_jump(self, op, fcond):
        assert self.jump_target_descr is None
        descr = op.getdescr()
        assert isinstance(descr, TargetToken)
        self.jump_target_descr = descr
        arglocs = self.assembler.target_arglocs(descr)

        # get temporary locs
        tmploc = r.ip
        vfptmploc = r.vfp_ip

        # Part about non-floats
        src_locations1 = []
        dst_locations1 = []
        # Part about floats
        src_locations2 = []
        dst_locations2 = []

        # Build the four lists
        for i in range(op.numargs()):
            box = op.getarg(i)
            src_loc = self.loc(box)
            dst_loc = arglocs[i]
            if box.type != FLOAT:
                src_locations1.append(src_loc)
                dst_locations1.append(dst_loc)
            else:
                src_locations2.append(src_loc)
                dst_locations2.append(dst_loc)
        self.assembler.check_frame_before_jump(self.jump_target_descr)
        remap_frame_layout_mixed(self.assembler,
                                 src_locations1, dst_locations1, tmploc,
                                 src_locations2, dst_locations2, vfptmploc)
        return []

    def prepare_op_setfield_gc(self, op, fcond):
        boxes = op.getarglist()
        a0, a1 = boxes
        ofs, size, sign = unpack_fielddescr(op.getdescr())
        base_loc = self.make_sure_var_in_reg(a0, boxes)
        value_loc = self.make_sure_var_in_reg(a1, boxes)
        ofs_size = default_imm_size if size < 8 else VMEM_imm_size
        if check_imm_arg(ofs, size=ofs_size):
            ofs_loc = imm(ofs)
        else:
            ofs_loc = self.get_scratch_reg(INT, boxes)
            self.assembler.load(ofs_loc, imm(ofs))
        return [value_loc, base_loc, ofs_loc, imm(size)]

    prepare_op_setfield_raw = prepare_op_setfield_gc

    def prepare_op_getfield_gc(self, op, fcond):
        a0 = op.getarg(0)
        ofs, size, sign = unpack_fielddescr(op.getdescr())
        base_loc = self.make_sure_var_in_reg(a0)
        immofs = imm(ofs)
        ofs_size = default_imm_size if size < 8 else VMEM_imm_size
        if check_imm_arg(ofs, size=ofs_size):
            ofs_loc = immofs
        else:
            ofs_loc = self.get_scratch_reg(INT, [a0])
            self.assembler.load(ofs_loc, immofs)
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op.result)
        return [base_loc, ofs_loc, res, imm(size)]

    prepare_op_getfield_raw = prepare_op_getfield_gc
    prepare_op_getfield_raw_pure = prepare_op_getfield_gc
    prepare_op_getfield_gc_pure = prepare_op_getfield_gc

    def prepare_op_increment_debug_counter(self, op, fcond):
        boxes = op.getarglist()
        a0, = boxes
        base_loc = self.make_sure_var_in_reg(a0, boxes)
        value_loc = self.get_scratch_reg(INT, boxes)
        self.free_temp_vars()
        return [base_loc, value_loc]

    def prepare_op_getinteriorfield_gc(self, op, fcond):
        t = unpack_interiorfielddescr(op.getdescr())
        ofs, itemsize, fieldsize, sign = t
        args = op.getarglist()
        base_loc = self.make_sure_var_in_reg(op.getarg(0), args)
        index_loc = self.make_sure_var_in_reg(op.getarg(1), args)
        immofs = imm(ofs)
        ofs_size = default_imm_size if fieldsize < 8 else VMEM_imm_size
        if check_imm_arg(ofs, size=ofs_size):
            ofs_loc = immofs
        else:
            ofs_loc = self.get_scratch_reg(INT, args)
            self.assembler.load(ofs_loc, immofs)
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        result_loc = self.force_allocate_reg(op.result)
        return [base_loc, index_loc, result_loc, ofs_loc, imm(ofs),
                                    imm(itemsize), imm(fieldsize)]

    def prepare_op_setinteriorfield_gc(self, op, fcond):
        t = unpack_interiorfielddescr(op.getdescr())
        ofs, itemsize, fieldsize, sign = t
        args = op.getarglist()
        base_loc = self.make_sure_var_in_reg(op.getarg(0), args)
        index_loc = self.make_sure_var_in_reg(op.getarg(1), args)
        value_loc = self.make_sure_var_in_reg(op.getarg(2), args)
        immofs = imm(ofs)
        ofs_size = default_imm_size if fieldsize < 8 else VMEM_imm_size
        if check_imm_arg(ofs, size=ofs_size):
            ofs_loc = immofs
        else:
            ofs_loc = self.get_scratch_reg(INT, args)
            self.assembler.load(ofs_loc, immofs)
        return [base_loc, index_loc, value_loc, ofs_loc, imm(ofs),
                                        imm(itemsize), imm(fieldsize)]
    prepare_op_setinteriorfield_raw = prepare_op_setinteriorfield_gc

    def prepare_op_arraylen_gc(self, op, fcond):
        arraydescr = op.getdescr()
        assert isinstance(arraydescr, ArrayDescr)
        ofs = arraydescr.lendescr.offset
        arg = op.getarg(0)
        base_loc = self.make_sure_var_in_reg(arg)
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op.result)
        return [res, base_loc, imm(ofs)]

    def prepare_op_setarrayitem_gc(self, op, fcond):
        size, ofs, _ = unpack_arraydescr(op.getdescr())
        scale = get_scale(size)
        args = op.getarglist()
        base_loc = self.make_sure_var_in_reg(args[0], args)
        value_loc = self.make_sure_var_in_reg(args[2], args)
        ofs_loc = self.make_sure_var_in_reg(args[1], args)
        assert check_imm_arg(ofs)
        return [value_loc, base_loc, ofs_loc, imm(scale), imm(ofs)]
    prepare_op_setarrayitem_raw = prepare_op_setarrayitem_gc
    prepare_op_raw_store = prepare_op_setarrayitem_gc

    def prepare_op_getarrayitem_gc(self, op, fcond):
        boxes = op.getarglist()
        size, ofs, _ = unpack_arraydescr(op.getdescr())
        scale = get_scale(size)
        base_loc = self.make_sure_var_in_reg(boxes[0], boxes)
        ofs_loc = self.make_sure_var_in_reg(boxes[1], boxes)
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op.result)
        assert check_imm_arg(ofs)
        return [res, base_loc, ofs_loc, imm(scale), imm(ofs)]

    prepare_op_getarrayitem_raw = prepare_op_getarrayitem_gc
    prepare_op_getarrayitem_raw_pure = prepare_op_getarrayitem_gc
    prepare_op_getarrayitem_gc_pure = prepare_op_getarrayitem_gc
    prepare_op_raw_load = prepare_op_getarrayitem_gc

    def prepare_op_strlen(self, op, fcond):
        args = op.getarglist()
        l0 = self.make_sure_var_in_reg(op.getarg(0))
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                         self.cpu.translate_support_code)
        immofs = imm(ofs_length)
        if check_imm_arg(ofs_length):
            l1 = immofs
        else:
            l1 = self.get_scratch_reg(INT, args)
            self.assembler.load(l1, immofs)

        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()

        res = self.force_allocate_reg(op.result)
        self.possibly_free_var(op.result)
        return [l0, l1, res]

    def prepare_op_strgetitem(self, op, fcond):
        boxes = op.getarglist()
        base_loc = self.make_sure_var_in_reg(boxes[0])

        a1 = boxes[1]
        imm_a1 = check_imm_box(a1)
        if imm_a1:
            ofs_loc = self.convert_to_imm(a1)
        else:
            ofs_loc = self.make_sure_var_in_reg(a1, boxes)

        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op.result)

        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                         self.cpu.translate_support_code)
        assert itemsize == 1
        return [res, base_loc, ofs_loc, imm(basesize)]

    def prepare_op_strsetitem(self, op, fcond):
        boxes = op.getarglist()
        base_loc = self.make_sure_var_in_reg(boxes[0], boxes)
        ofs_loc = self.make_sure_var_in_reg(boxes[1], boxes)
        value_loc = self.make_sure_var_in_reg(boxes[2], boxes)
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                         self.cpu.translate_support_code)
        assert itemsize == 1
        return [value_loc, base_loc, ofs_loc, imm(basesize)]

    prepare_op_copystrcontent = void
    prepare_op_copyunicodecontent = void

    def prepare_op_unicodelen(self, op, fcond):
        l0 = self.make_sure_var_in_reg(op.getarg(0))
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                         self.cpu.translate_support_code)
        immofs = imm(ofs_length)
        if check_imm_arg(ofs_length):
            l1 = immofs
        else:
            l1 = self.get_scratch_reg(INT, [op.getarg(0)])
            self.assembler.load(l1, immofs)

        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op.result)
        return [l0, l1, res]

    def prepare_op_unicodegetitem(self, op, fcond):
        boxes = op.getarglist()
        base_loc = self.make_sure_var_in_reg(boxes[0], boxes)
        ofs_loc = self.make_sure_var_in_reg(boxes[1], boxes)

        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op.result)

        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                         self.cpu.translate_support_code)
        scale = itemsize / 2
        return [res, base_loc, ofs_loc,
            imm(scale), imm(basesize), imm(itemsize)]

    def prepare_op_unicodesetitem(self, op, fcond):
        boxes = op.getarglist()
        base_loc = self.make_sure_var_in_reg(boxes[0], boxes)
        ofs_loc = self.make_sure_var_in_reg(boxes[1], boxes)
        value_loc = self.make_sure_var_in_reg(boxes[2], boxes)
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                         self.cpu.translate_support_code)
        scale = itemsize / 2
        return [value_loc, base_loc, ofs_loc,
            imm(scale), imm(basesize), imm(itemsize)]

    def prepare_op_same_as(self, op, fcond):
        arg = op.getarg(0)
        imm_arg = check_imm_box(arg)
        if imm_arg:
            argloc = self.convert_to_imm(arg)
        else:
            argloc = self.make_sure_var_in_reg(arg)
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        resloc = self.force_allocate_reg(op.result)
        return [argloc, resloc]

    prepare_op_cast_ptr_to_int = prepare_op_same_as
    prepare_op_cast_int_to_ptr = prepare_op_same_as

    def prepare_op_call_malloc_nursery(self, op, fcond):
        size_box = op.getarg(0)
        assert isinstance(size_box, ConstInt)
        size = size_box.getint()

        self.rm.force_allocate_reg(op.result, selected_reg=r.r0)
        t = TempInt()
        self.rm.force_allocate_reg(t, selected_reg=r.r1)

        sizeloc = size_box.getint()
        gc_ll_descr = self.cpu.gc_ll_descr
        gcmap = self.get_gcmap([r.r0, r.r1])
        self.possibly_free_var(t)
        self.assembler.malloc_cond(
            gc_ll_descr.get_nursery_free_addr(),
            gc_ll_descr.get_nursery_top_addr(),
            sizeloc,
            gcmap
            )
        self.assembler._alignment_check()

    def prepare_op_call_malloc_nursery_varsize_frame(self, op, fcond):
        size_box = op.getarg(0)
        assert isinstance(size_box, BoxInt) # we cannot have a const here!
        # sizeloc must be in a register, but we can free it now
        # (we take care explicitly of conflicts with r0 or r1)
        sizeloc = self.rm.make_sure_var_in_reg(size_box)
        self.rm.possibly_free_var(size_box)
        #
        self.rm.force_allocate_reg(op.result, selected_reg=r.r0)
        #
        t = TempInt()
        self.rm.force_allocate_reg(t, selected_reg=r.r1)
        #
        gcmap = self.get_gcmap([r.r0, r.r1])
        self.possibly_free_var(t)
        #
        gc_ll_descr = self.assembler.cpu.gc_ll_descr
        self.assembler.malloc_cond_varsize_frame(
            gc_ll_descr.get_nursery_free_addr(),
            gc_ll_descr.get_nursery_top_addr(),
            sizeloc,
            gcmap
            )
        self.assembler._alignment_check()

    def prepare_op_call_malloc_nursery_varsize(self, op, fcond):
        gc_ll_descr = self.assembler.cpu.gc_ll_descr
        if not hasattr(gc_ll_descr, 'max_size_of_young_obj'):
            raise Exception("unreachable code")
            # for boehm, this function should never be called
        arraydescr = op.getdescr()
        length_box = op.getarg(2)
        assert isinstance(length_box, BoxInt) # we cannot have a const here!
        # the result will be in r0
        self.rm.force_allocate_reg(op.result, selected_reg=r.r0)
        # we need r1 as a temporary
        tmp_box = TempBox()
        self.rm.force_allocate_reg(tmp_box, selected_reg=r.r1)
        gcmap = self.get_gcmap([r.r0, r.r1]) # allocate the gcmap *before*
        self.rm.possibly_free_var(tmp_box)
        # length_box always survives: it's typically also present in the
        # next operation that will copy it inside the new array.  It's
        # fine to load it from the stack too, as long as it's != r0, r1.
        lengthloc = self.rm.loc(length_box)
        self.rm.possibly_free_var(length_box)
        #
        itemsize = op.getarg(1).getint()
        maxlength = (gc_ll_descr.max_size_of_young_obj - WORD * 2) / itemsize
        self.assembler.malloc_cond_varsize(
            op.getarg(0).getint(),
            gc_ll_descr.get_nursery_free_addr(),
            gc_ll_descr.get_nursery_top_addr(),
            lengthloc, itemsize, maxlength, gcmap, arraydescr)

    prepare_op_debug_merge_point = void
    prepare_op_jit_debug = void
    prepare_op_keepalive = void

    def prepare_op_cond_call_gc_wb(self, op, fcond):
        assert op.result is None
        # we force all arguments in a reg because it will be needed anyway by
        # the following setfield_gc or setarrayitem_gc. It avoids loading it
        # twice from the memory.
        N = op.numargs()
        args = op.getarglist()
        arglocs = [self.make_sure_var_in_reg(op.getarg(i), args)
                                                              for i in range(N)]
        tmp = self.get_scratch_reg(INT, args)
        assert tmp not in arglocs
        arglocs.append(tmp)
        return arglocs

    prepare_op_cond_call_gc_wb_array = prepare_op_cond_call_gc_wb

    def prepare_op_cond_call(self, op, fcond):
        assert op.result is None
        assert 2 <= op.numargs() <= 4 + 2
        tmpreg = self.get_scratch_reg(INT, selected_reg=r.r4)
        v = op.getarg(1)
        assert isinstance(v, Const)
        imm = self.rm.convert_to_imm(v)
        self.assembler.regalloc_mov(imm, tmpreg)
        args_so_far = []
        for i in range(2, op.numargs()):
            reg = r.argument_regs[i - 2]
            arg = op.getarg(i)
            self.make_sure_var_in_reg(arg, args_so_far, selected_reg=reg)
            args_so_far.append(arg)
        loc_cond = self.make_sure_var_in_reg(op.getarg(0), args_so_far)
        gcmap = self.get_gcmap([tmpreg])
        self.assembler.cond_call(op, gcmap, loc_cond, tmpreg, fcond)

    def prepare_op_force_token(self, op, fcond):
        # XXX for now we return a regular reg
        res_loc = self.force_allocate_reg(op.result)
        self.possibly_free_var(op.result)
        return [res_loc]

    def prepare_op_label(self, op, fcond):
        descr = op.getdescr()
        assert isinstance(descr, TargetToken)
        inputargs = op.getarglist()
        arglocs = [None] * len(inputargs)
        #
        # we use force_spill() on the boxes that are not going to be really
        # used any more in the loop, but that are kept alive anyway
        # by being in a next LABEL's or a JUMP's argument or fail_args
        # of some guard
        position = self.rm.position
        for arg in inputargs:
            assert isinstance(arg, Box)
            if self.last_real_usage.get(arg, -1) <= position:
                self.force_spill_var(arg)

        #
        for i in range(len(inputargs)):
            arg = inputargs[i]
            assert isinstance(arg, Box)
            loc = self.loc(arg)
            arglocs[i] = loc
            if loc.is_core_reg() or loc.is_vfp_reg():
                self.frame_manager.mark_as_free(arg)
        #
        descr._arm_arglocs = arglocs
        descr._ll_loop_code = self.assembler.mc.currpos()
        descr._arm_clt = self.assembler.current_clt
        self.assembler.target_tokens_currently_compiling[descr] = None
        self.possibly_free_vars_for_op(op)
        #
        # if the LABEL's descr is precisely the target of the JUMP at the
        # end of the same loop, i.e. if what we are compiling is a single
        # loop that ends up jumping to this LABEL, then we can now provide
        # the hints about the expected position of the spilled variables.
        #jump_op = self.final_jump_op
        #if jump_op is not None and jump_op.getdescr() is descr:
        #    self._compute_hint_frame_locations_from_descr(descr)
        return []

    def prepare_op_guard_not_forced_2(self, op, fcond):
        self.rm.before_call(op.getfailargs(), save_all_regs=True)
        fail_locs = self._prepare_guard(op)
        self.assembler.store_force_descr(op, fail_locs[1:], fail_locs[0].value)
        self.possibly_free_vars(op.getfailargs())

    def prepare_guard_call_may_force(self, op, guard_op, fcond):
        args = self._prepare_call(op, save_all_regs=True)
        return self._prepare_guard(guard_op, args)
    prepare_guard_call_release_gil = prepare_guard_call_may_force

    def prepare_guard_call_assembler(self, op, guard_op, fcond):
        locs = self.locs_for_call_assembler(op, guard_op)
        tmploc = self.get_scratch_reg(INT, selected_reg=r.r0)
        resloc = self._call(op, locs + [tmploc], save_all_regs=True)
        self.possibly_free_vars(guard_op.getfailargs())
        return locs + [resloc, tmploc]

    def _prepare_args_for_new_op(self, new_args):
        gc_ll_descr = self.cpu.gc_ll_descr
        args = gc_ll_descr.args_for_new(new_args)
        arglocs = []
        for i in range(len(args)):
            arg = args[i]
            t = TempInt()
            l = self.force_allocate_reg(t, selected_reg=r.all_regs[i])
            self.assembler.load(l, imm(arg))
            arglocs.append(t)
        return arglocs

    prepare_op_float_add = prepare_float_op(name='prepare_op_float_add')
    prepare_op_float_sub = prepare_float_op(name='prepare_op_float_sub')
    prepare_op_float_mul = prepare_float_op(name='prepare_op_float_mul')
    prepare_op_float_truediv = prepare_float_op(name='prepare_op_float_truediv')
    prepare_op_float_lt = prepare_float_op(float_result=False,
                                            name='prepare_op_float_lt')
    prepare_op_float_le = prepare_float_op(float_result=False,
                                            name='prepare_op_float_le')
    prepare_op_float_eq = prepare_float_op(float_result=False,
                                            name='prepare_op_float_eq')
    prepare_op_float_ne = prepare_float_op(float_result=False,
                                            name='prepare_op_float_ne')
    prepare_op_float_gt = prepare_float_op(float_result=False,
                                            name='prepare_op_float_gt')
    prepare_op_float_ge = prepare_float_op(float_result=False,
                                            name='prepare_op_float_ge')
    prepare_op_float_neg = prepare_float_op(base=False,
                                            name='prepare_op_float_neg')
    prepare_op_float_abs = prepare_float_op(base=False,
                                            name='prepare_op_float_abs')

    prepare_guard_float_lt = prepare_float_op(guard=True,
                            float_result=False, name='prepare_guard_float_lt')
    prepare_guard_float_le = prepare_float_op(guard=True,
                            float_result=False, name='prepare_guard_float_le')
    prepare_guard_float_eq = prepare_float_op(guard=True,
                            float_result=False, name='prepare_guard_float_eq')
    prepare_guard_float_ne = prepare_float_op(guard=True,
                            float_result=False, name='prepare_guard_float_ne')
    prepare_guard_float_gt = prepare_float_op(guard=True,
                            float_result=False, name='prepare_guard_float_gt')
    prepare_guard_float_ge = prepare_float_op(guard=True,
                            float_result=False, name='prepare_guard_float_ge')

    def prepare_op_math_sqrt(self, op, fcond):
        loc = self.make_sure_var_in_reg(op.getarg(1))
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.vfprm.force_allocate_reg(op.result)
        self.possibly_free_var(op.result)
        return [loc, res]

    def prepare_op_cast_float_to_int(self, op, fcond):
        loc1 = self.make_sure_var_in_reg(op.getarg(0))
        res = self.rm.force_allocate_reg(op.result)
        return [loc1, res]

    def prepare_op_cast_int_to_float(self, op, fcond):
        loc1 = self.make_sure_var_in_reg(op.getarg(0))
        res = self.vfprm.force_allocate_reg(op.result)
        return [loc1, res]

    def prepare_force_spill(self, op, fcond):
        self.force_spill_var(op.getarg(0))
        return []

    prepare_op_convert_float_bytes_to_longlong = prepare_float_op(base=False,
                              name='prepare_op_convert_float_bytes_to_longlong')
    prepare_op_convert_longlong_bytes_to_float = prepare_float_op(base=False,
                              name='prepare_op_convert_longlong_bytes_to_float')

    def prepare_op_read_timestamp(self, op, fcond):
        loc = self.get_scratch_reg(INT)
        res = self.vfprm.force_allocate_reg(op.result)
        return [loc, res]

    def prepare_op_cast_float_to_singlefloat(self, op, fcond):
        loc1 = self.make_sure_var_in_reg(op.getarg(0))
        res = self.force_allocate_reg(op.result)
        return [loc1, res]

    def prepare_op_cast_singlefloat_to_float(self, op, fcond):
        loc1 = self.make_sure_var_in_reg(op.getarg(0))
        res = self.force_allocate_reg(op.result)
        return [loc1, res]


def add_none_argument(fn):
    return lambda self, op, fcond: fn(self, op, None, fcond)


def notimplemented(self, op, fcond):
    print "[ARM/regalloc] %s not implemented" % op.getopname()
    raise NotImplementedError(op)


def notimplemented_with_guard(self, op, guard_op, fcond):
    print "[ARM/regalloc] %s with guard %s not implemented" % \
                        (op.getopname(), guard_op.getopname())
    raise NotImplementedError(op)

operations = [notimplemented] * (rop._LAST + 1)
operations_with_guard = [notimplemented_with_guard] * (rop._LAST + 1)


for key, value in rop.__dict__.items():
    key = key.lower()
    if key.startswith('_'):
        continue
    methname = 'prepare_op_%s' % key
    if hasattr(Regalloc, methname):
        func = getattr(Regalloc, methname).im_func
        operations[value] = func

for key, value in rop.__dict__.items():
    key = key.lower()
    if key.startswith('_'):
        continue
    methname = 'prepare_guard_%s' % key
    if hasattr(Regalloc, methname):
        func = getattr(Regalloc, methname).im_func
        operations_with_guard[value] = func
        operations[value] = add_none_argument(func)

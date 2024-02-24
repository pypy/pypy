#!/usr/bin/env python

from rpython.jit.backend.llsupport import rewrite
from rpython.jit.backend.llsupport.descr import CallDescr
from rpython.jit.backend.llsupport.gcmap import allocate_gcmap
from rpython.jit.backend.llsupport.jump import remap_frame_layout_mixed
from rpython.jit.backend.llsupport.regalloc import (
    BaseRegalloc, FrameManager, RegisterManager, TempVar,
    compute_vars_longevity)
from rpython.jit.backend.riscv import registers as r
from rpython.jit.backend.riscv.arch import (
    JITFRAME_FIXED_SIZE, SHAMT_MAX, SINT12_IMM_MAX, SINT12_IMM_MIN, XLEN)
from rpython.jit.backend.riscv.instruction_util import (
    COND_BEQ, COND_BGE, COND_BGEU, COND_BLT, COND_BLTU, COND_BNE, COND_INVALID,
    check_imm_arg, get_negated_branch_inst)
from rpython.jit.backend.riscv.locations import (
    FloatImmLocation, ImmLocation, StackLocation, get_fp_offset)
from rpython.jit.backend.riscv.opassembler import asm_comp_operations
from rpython.jit.codewriter import longlong
from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.jit.metainterp.history import (
    Const, ConstFloat, ConstInt, ConstPtr, FLOAT, INT, REF, TargetToken)
from rpython.jit.metainterp.resoperation import rop
from rpython.rlib.rarithmetic import r_uint
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.lltypesystem.lloperation import llop


class TempInt(TempVar):
    type = INT

    def __repr__(self):
        return "<TempInt at %s>" % (id(self),)


class TempPtr(TempVar):
    type = REF

    def __repr__(self):
        return "<TempPtr at %s>" % (id(self),)


class TempFloat(TempVar):
    type = FLOAT

    def __repr__(self):
        return "<TempFloat at %s>" % (id(self),)


class RISCVFrameManager(FrameManager):
    def __init__(self, base_ofs):
        FrameManager.__init__(self)
        self.base_ofs = base_ofs

    def frame_pos(self, i, box_type):
        return StackLocation(i, get_fp_offset(self.base_ofs, i), box_type)

    @staticmethod
    def frame_size(type):
        # Returns the number of stack slots that are required to hold the
        # variable of `type`.
        #
        # In RV64IMAFD, both integer, float, and pointer types are 64-bit.  The
        # stack slot size is defined as 64-bit.  Thus, we return 1 regardless
        # the `type`.
        #
        # TODO: In RV32IMAFD, the integer and pointer types are 32-bit but the
        # float type is 64-bit (i.e. represent Python `float` value with double
        # precision floating point).  The stack slot size should be defined as
        # 32-bit.  We should return 2 when the `type` is `FLOAT` and return 1
        # otherwise.
        #
        # Note: `FrameManager.get_new_loc()` guarantees that the position is
        # always a multiple of size.
        return 1

    @staticmethod
    def get_loc_index(loc):
        assert loc.is_stack()
        return loc.position


class RISCVRegisterManager(RegisterManager):
    # Registers assigned to temp boxes must not be spilled before
    # `free_temp_vars()` is called.
    #
    # This ensures that the constant register allocated by `return_constant`
    # is not spilled by subsequent `make_sure_var_in_reg` (Note: passing
    # `op.getarglist()` as the `forbidden_vars` argument is not sufficient
    # because `get_scratch_reg` associates the register with `TempInt`,
    # `TempPtr`, or `TempFloat` instead of `ConstInt`, `ConstPtr`, or
    # `ConstFloat`.)
    FORBID_TEMP_BOXES = True


class CoreRegisterManager(RISCVRegisterManager):
    all_regs = r.allocatable_registers
    box_types = None
    no_lower_byte_regs = all_regs
    save_around_call_regs = r.caller_saved_registers
    frame_reg = r.jfp

    def __init__(self, longevity, frame_manager=None, assembler=None):
        RISCVRegisterManager.__init__(self, longevity, frame_manager,
                                      assembler)

    def call_result_location(self, v):
        return r.x10

    def convert_to_imm(self, c):
        # Note: `c.value` below have different types.
        if isinstance(c, ConstInt):
            val = rffi.cast(lltype.Signed, c.value)
        else:
            assert isinstance(c, ConstPtr)
            val = rffi.cast(lltype.Signed, c.value)
        return ImmLocation(val)

    def return_constant(self, v, forbidden_vars=[], selected_reg=None):
        self._check_type(v)
        if isinstance(v, Const):
            if isinstance(v, ConstInt):
                reg_type = INT
            else:
                assert isinstance(v, ConstPtr)
                reg_type = REF

            if not v.nonnull() and selected_reg is None:
                return r.zero

            loc = self.get_scratch_reg(reg_type, forbidden_vars,
                                       selected_reg=selected_reg)
            immvalue = self.convert_to_imm(v)
            self.assembler.load_imm(loc, immvalue)
            return loc
        return RISCVRegisterManager.return_constant(self, v, forbidden_vars,
                                                    selected_reg)

    def get_scratch_reg(self, type=INT, forbidden_vars=[], selected_reg=None):
        assert type == INT or type == REF
        box = None
        if type == INT:
            box = TempInt()
        else:
            box = TempPtr()
        reg = self.force_allocate_reg(box, forbidden_vars=forbidden_vars,
                                      selected_reg=selected_reg)
        self.temp_boxes.append(box)
        return reg


class FloatRegisterManager(RISCVRegisterManager):
    all_regs = r.allocatable_fp_registers
    box_types = [FLOAT]
    save_around_call_regs = r.caller_saved_fp_registers

    def __init__(self, longevity, frame_manager=None, assembler=None):
        RISCVRegisterManager.__init__(self, longevity, frame_manager,
                                      assembler)

    def call_result_location(self, v):
        return r.f10

    def convert_to_imm(self, c):
        imm_bits = longlong.extract_bits(c.getfloatstorage())
        return FloatImmLocation(imm_bits)

    def return_constant(self, v, forbidden_vars=[], selected_reg=None):
        self._check_type(v)
        if isinstance(v, Const):
            assert isinstance(v, ConstFloat)
            loc = self.get_scratch_reg(FLOAT, forbidden_vars,
                                       selected_reg=selected_reg)
            immvalue = self.convert_to_imm(v)
            self.assembler.load_imm(loc, immvalue)
            return loc
        return RISCVRegisterManager.return_constant(self, v, forbidden_vars,
                                                    selected_reg)

    def get_scratch_reg(self, type=FLOAT, forbidden_vars=[], selected_reg=None):
        assert type == FLOAT
        box = TempFloat()
        reg = self.force_allocate_reg(box, forbidden_vars=forbidden_vars,
                                      selected_reg=selected_reg)
        self.temp_boxes.append(box)
        return reg


def check_imm_box(arg):
    if isinstance(arg, ConstInt):
        return check_imm_arg(arg.getint())
    return False

def check_negative_imm_box(arg):
    if isinstance(arg, ConstInt):
        return check_imm_arg(-arg.getint())
    return False

def check_plus_one_imm_box(arg):
    if isinstance(arg, ConstInt):
        return check_imm_arg(arg.getint() + 1)
    return False

def check_uint_le_rhs_imm_arg(imm):
    return imm >= SINT12_IMM_MIN - 1 and imm <= SINT12_IMM_MAX - 1

def check_uint_le_rhs_imm_box(arg):
    if isinstance(arg, ConstInt):
        return check_uint_le_rhs_imm_arg(arg.getint())
    return False

def check_shamt_imm_arg(imm):
    return imm >= 0 and imm <= SHAMT_MAX

def check_shamt_imm_box(arg):
    if isinstance(arg, ConstInt):
        return check_shamt_imm_arg(arg.getint())
    return False


class Regalloc(BaseRegalloc):
    def __init__(self, assembler):
        self.cpu = assembler.cpu
        self.assembler = assembler
        self.frame_manager = None
        self.rm = None
        self.fprm = None
        self.jump_target_descr = None
        self.final_jump_op = None

    def _prepare(self, inputargs, operations, allgcrefs):
        cpu = self.cpu

        self.fm = RISCVFrameManager(cpu.get_baseofs_of_frame_field())
        self.frame_manager = self.fm
        operations = cpu.gc_ll_descr.rewrite_assembler(cpu, operations,
                                                       allgcrefs)

        longevity = compute_vars_longevity(inputargs, operations)
        self.longevity = longevity

        self.rm = CoreRegisterManager(longevity, self.fm, self.assembler)
        self.fprm = FloatRegisterManager(longevity, self.fm, self.assembler)
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

    def _update_bindings(self, locs, inputargs):
        # Bind the boxes to locations (e.g. registers or stack slots).
        used = {}
        i = 0
        for loc in locs:
            if loc is None:
                loc = r.jfp
            arg = inputargs[i]
            i += 1
            if loc.is_core_reg():
                self.rm.reg_bindings[arg] = loc
                used[loc] = None
            elif loc.is_fp_reg():
                self.fprm.reg_bindings[arg] = loc
                used[loc] = None
            else:
                assert loc.is_stack()
                self.frame_manager.bind(arg, loc)

        # Collect the free registers.
        self.rm.free_regs = []
        for reg in self.rm.all_regs:
            if reg not in used:
                self.rm.free_regs.append(reg)
        self.fprm.free_regs = []
        for reg in self.fprm.all_regs:
            if reg not in used:
                self.fprm.free_regs.append(reg)

        # Note: we need to make a copy of inputargs because possibly_free_vars
        # is also used on op args, which is a non-resizable list.
        self.possibly_free_vars(list(inputargs))

        self.frame_manager.finish_binding()
        self._check_invariants()

    def _prepare_op_int_commutative_binary_op(self, op):
        boxes = op.getarglist()
        a0, a1 = boxes
        imm_a0 = check_imm_box(a0)
        imm_a1 = check_imm_box(a1)
        if not imm_a0 and imm_a1:
            l0 = self.make_sure_var_in_reg(a0, boxes)
            l1 = self.convert_to_imm(a1)
        elif imm_a0 and not imm_a1:
            l1 = self.convert_to_imm(a0)
            l0 = self.make_sure_var_in_reg(a1, boxes)
        else:
            l0 = self.make_sure_var_in_reg(a0, boxes)
            l1 = self.make_sure_var_in_reg(a1, boxes)
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op)
        return [l0, l1, res]

    prepare_op_int_add = _prepare_op_int_commutative_binary_op
    prepare_op_int_and = _prepare_op_int_commutative_binary_op
    prepare_op_int_or  = _prepare_op_int_commutative_binary_op
    prepare_op_int_xor = _prepare_op_int_commutative_binary_op
    prepare_op_nursery_ptr_increment = _prepare_op_int_commutative_binary_op

    def prepare_op_int_sub(self, op):
        boxes = op.getarglist()
        a0, a1 = boxes
        # int_sub immediate is lowered into addi with negative immediate, thus
        # we have to check whether the negative immediate can be kept in
        # simm12.
        if check_negative_imm_box(a1):
            l0 = self.make_sure_var_in_reg(a0, boxes)
            l1 = self.convert_to_imm(a1)
        else:
            l0 = self.make_sure_var_in_reg(a0, boxes)
            l1 = self.make_sure_var_in_reg(a1, boxes)
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op)
        return [l0, l1, res]

    def _prepare_op_int_mul_op(self, op):
        boxes = op.getarglist()
        a0, a1 = boxes
        l0 = self.make_sure_var_in_reg(a0, boxes)
        l1 = self.make_sure_var_in_reg(a1, boxes)
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op)
        return [l0, l1, res]

    prepare_op_int_mul = _prepare_op_int_mul_op
    prepare_op_uint_mul_high = _prepare_op_int_mul_op

    def _prepare_op_int_shift_op(self, op):
        boxes = op.getarglist()
        a0, a1 = boxes
        if check_shamt_imm_box(a1):
            l0 = self.make_sure_var_in_reg(a0, boxes)
            l1 = self.convert_to_imm(a1)
        else:
            l0 = self.make_sure_var_in_reg(a0, boxes)
            l1 = self.make_sure_var_in_reg(a1, boxes)
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op)
        return [l0, l1, res]

    prepare_op_int_lshift = _prepare_op_int_shift_op
    prepare_op_int_rshift = _prepare_op_int_shift_op
    prepare_op_uint_rshift = _prepare_op_int_shift_op

    def _gen_prepare_op_int_lt(swap_operands):
        def _prepare_op_int_lt(self, op):
            boxes = op.getarglist()

            if swap_operands:
                a1, a0 = boxes
            else:
                a0, a1 = boxes

            if check_imm_box(a1):
                l0 = self.make_sure_var_in_reg(a0, boxes)
                l1 = self.convert_to_imm(a1)
            else:
                l0 = self.make_sure_var_in_reg(a0, boxes)
                l1 = self.make_sure_var_in_reg(a1, boxes)

            self.possibly_free_vars_for_op(op)
            self.free_temp_vars()
            res = self.force_allocate_reg(op)
            return [l0, l1, res]
        return _prepare_op_int_lt

    prepare_op_int_lt = _gen_prepare_op_int_lt(swap_operands=False)
    prepare_op_int_gt = _gen_prepare_op_int_lt(swap_operands=True)

    prepare_op_uint_lt = prepare_op_int_lt
    prepare_op_uint_gt = prepare_op_int_gt

    prepare_comp_op_int_lt = prepare_op_int_lt
    prepare_comp_op_int_gt = prepare_op_int_gt

    prepare_comp_op_uint_lt = prepare_op_uint_lt
    prepare_comp_op_uint_gt = prepare_op_uint_gt

    def _gen_prepare_op_int_le(swap_operands):
        def _prepare_op_int_le(self, op):
            boxes = op.getarglist()

            if swap_operands:
                a1, a0 = boxes
            else:
                a0, a1 = boxes

            if check_plus_one_imm_box(a1):
                l0 = self.make_sure_var_in_reg(a0, boxes)
                l1 = self.convert_to_imm(a1)
            elif check_imm_box(a0):
                l0 = self.convert_to_imm(a0)
                l1 = self.make_sure_var_in_reg(a1, boxes)
            else:
                l0 = self.make_sure_var_in_reg(a0, boxes)
                l1 = self.make_sure_var_in_reg(a1, boxes)

            self.possibly_free_vars_for_op(op)
            self.free_temp_vars()
            res = self.force_allocate_reg(op)
            return [l0, l1, res]
        return _prepare_op_int_le

    prepare_op_int_le = _gen_prepare_op_int_le(swap_operands=False)
    prepare_op_int_ge = _gen_prepare_op_int_le(swap_operands=True)

    prepare_comp_op_int_le = prepare_op_int_le
    prepare_comp_op_int_ge = prepare_op_int_ge

    def _gen_prepare_op_uint_le(swap_operands):
        def _prepare_op_uint_le(self, op):
            boxes = op.getarglist()

            if swap_operands:
                a1, a0 = boxes
            else:
                a0, a1 = boxes

            if check_uint_le_rhs_imm_box(a1):
                l0 = self.make_sure_var_in_reg(a0, boxes)
                l1 = self.convert_to_imm(a1)
            elif check_imm_box(a0):
                l0 = self.convert_to_imm(a0)
                l1 = self.make_sure_var_in_reg(a1, boxes)
            else:
                l0 = self.make_sure_var_in_reg(a0, boxes)
                l1 = self.make_sure_var_in_reg(a1, boxes)

            self.possibly_free_vars_for_op(op)
            self.free_temp_vars()
            res = self.force_allocate_reg(op)
            return [l0, l1, res]
        return _prepare_op_uint_le

    prepare_op_uint_le = _gen_prepare_op_uint_le(swap_operands=False)
    prepare_op_uint_ge = _gen_prepare_op_uint_le(swap_operands=True)

    prepare_comp_op_uint_le = prepare_op_uint_le
    prepare_comp_op_uint_ge = prepare_op_uint_ge

    def _prepare_op_int_commutative_compare_op(self, op):
        boxes = op.getarglist()
        a0, a1 = boxes
        imm_a0 = check_imm_box(a0)
        imm_a1 = check_imm_box(a1)
        if not imm_a0 and imm_a1:
            l0 = self.make_sure_var_in_reg(a0, boxes)
            l1 = self.convert_to_imm(a1)
        elif imm_a0 and not imm_a1:
            l1 = self.convert_to_imm(a0)
            l0 = self.make_sure_var_in_reg(a1, boxes)
        else:
            l0 = self.make_sure_var_in_reg(a0, boxes)
            l1 = self.make_sure_var_in_reg(a1, boxes)
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op)
        return [l0, l1, res]

    prepare_op_int_eq = _prepare_op_int_commutative_compare_op
    prepare_op_int_ne = _prepare_op_int_commutative_compare_op

    prepare_comp_op_int_eq = prepare_op_int_eq
    prepare_comp_op_int_ne = prepare_op_int_ne

    prepare_op_ptr_eq = prepare_op_instance_ptr_eq = prepare_op_int_eq
    prepare_op_ptr_ne = prepare_op_instance_ptr_ne = prepare_op_int_ne

    prepare_comp_op_ptr_eq = prepare_op_int_eq
    prepare_comp_op_ptr_ne = prepare_op_int_ne

    def _prepare_op_unary_op(self, op):
        boxes = op.getarglist()
        a0 = boxes[0]
        l0 = self.make_sure_var_in_reg(a0, boxes)
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op)
        return [l0, res]

    prepare_op_int_is_true = _prepare_op_unary_op
    prepare_op_int_neg = _prepare_op_unary_op
    prepare_op_int_invert = _prepare_op_unary_op
    prepare_op_int_is_zero = _prepare_op_unary_op
    prepare_op_int_force_ge_zero = _prepare_op_unary_op

    prepare_comp_op_int_is_true = prepare_op_int_is_true
    prepare_comp_op_int_is_zero = prepare_op_int_is_zero

    def prepare_op_int_signext(self, op):
        a0, a1 = op.getarglist()
        l0 = self.loc(a0)
        if l0.is_stack():
            # If a0 is on the stack, we can perform sign extension directly
            # with LB/LH/LW.
            pass
        else:
            # If a0 is not on the stack, we make sure it is in the register and
            # perform sign extension with SLLI/SRAI.
            l0 = self.make_sure_var_in_reg(a0)
        l1 = self.convert_to_imm(a1)  # num_bytes
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op)
        return [l0, l1, res]

    def _gen_prepare_op_float_binary_op(swap_operands):
        def _prepare_op_float_binary_op(self, op):
            boxes = op.getarglist()
            if swap_operands:
                a1, a0 = boxes
            else:
                a0, a1 = boxes
            l0 = self.make_sure_var_in_reg(a0, boxes)
            l1 = self.make_sure_var_in_reg(a1, boxes)
            self.possibly_free_vars_for_op(op)
            self.free_temp_vars()
            res = self.force_allocate_reg(op)
            return [l0, l1, res]
        return _prepare_op_float_binary_op

    _prepare_op_float_binary_op = _gen_prepare_op_float_binary_op(False)
    _prepare_op_float_binary_op_swapped = _gen_prepare_op_float_binary_op(True)

    prepare_op_float_add = _prepare_op_float_binary_op
    prepare_op_float_sub = _prepare_op_float_binary_op
    prepare_op_float_mul = _prepare_op_float_binary_op
    prepare_op_float_truediv = _prepare_op_float_binary_op

    prepare_op_float_lt = _prepare_op_float_binary_op
    prepare_op_float_le = _prepare_op_float_binary_op
    prepare_op_float_gt = _prepare_op_float_binary_op_swapped
    prepare_op_float_ge = _prepare_op_float_binary_op_swapped
    prepare_op_float_eq = _prepare_op_float_binary_op
    prepare_op_float_ne = _prepare_op_float_binary_op

    prepare_comp_op_float_lt = prepare_op_float_lt
    prepare_comp_op_float_le = prepare_op_float_le
    prepare_comp_op_float_gt = prepare_op_float_gt
    prepare_comp_op_float_ge = prepare_op_float_ge
    prepare_comp_op_float_eq = prepare_op_float_eq
    prepare_comp_op_float_ne = prepare_op_float_ne

    prepare_op_float_neg = _prepare_op_unary_op
    prepare_op_float_abs = _prepare_op_unary_op
    prepare_op_cast_float_to_int = _prepare_op_unary_op
    prepare_op_cast_int_to_float = _prepare_op_unary_op
    prepare_op_convert_float_bytes_to_longlong = _prepare_op_unary_op
    prepare_op_convert_longlong_bytes_to_float= _prepare_op_unary_op

    def prepare_op_gc_store(self, op):
        boxes = op.getarglist()
        base_loc = self.make_sure_var_in_reg(boxes[0], boxes)
        ofs = boxes[1]
        if check_imm_box(ofs):
            ofs_loc = self.convert_to_imm(ofs)
        else:
            ofs_loc = self.make_sure_var_in_reg(ofs, boxes)
        value_loc = self.make_sure_var_in_reg(boxes[2], boxes)
        size_loc = self.convert_to_imm(boxes[3])
        return [value_loc, base_loc, ofs_loc, size_loc]

    def _prepare_op_gc_load(self, op):
        boxes = op.getarglist()
        base_loc = self.make_sure_var_in_reg(boxes[0], boxes)
        ofs = boxes[1]
        if check_imm_box(ofs):
            ofs_loc = self.convert_to_imm(ofs)
        else:
            ofs_loc = self.make_sure_var_in_reg(ofs, boxes)
        nsize_loc = self.convert_to_imm(boxes[2])  # Negative for "signed"
        self.possibly_free_vars_for_op(op)
        res_loc = self.force_allocate_reg(op)
        return [base_loc, ofs_loc, res_loc, nsize_loc]

    prepare_op_gc_load_i = _prepare_op_gc_load
    prepare_op_gc_load_r = _prepare_op_gc_load
    prepare_op_gc_load_f = _prepare_op_gc_load

    def prepare_op_gc_store_indexed(self, op):
        boxes = op.getarglist()
        base_loc = self.make_sure_var_in_reg(boxes[0], boxes)
        index_loc = self.make_sure_var_in_reg(boxes[1], boxes)
        value_loc = self.make_sure_var_in_reg(boxes[2], boxes)
        assert boxes[3].getint() == 1  # scale
        ofs = boxes[4]
        if check_imm_box(ofs):
            ofs_loc = self.convert_to_imm(ofs)
        else:
            ofs_loc = self.make_sure_var_in_reg(ofs, boxes)
        size_loc = self.convert_to_imm(boxes[5])
        return [value_loc, base_loc, index_loc, ofs_loc, size_loc]

    def _prepare_op_gc_load_indexed(self, op):
        boxes = op.getarglist()
        base_loc = self.make_sure_var_in_reg(boxes[0], boxes)
        index_loc = self.make_sure_var_in_reg(boxes[1], boxes)
        assert boxes[2].getint() == 1  # scale
        ofs = boxes[3]
        if check_imm_box(ofs):
            ofs_loc = self.convert_to_imm(ofs)
        else:
            ofs_loc = self.make_sure_var_in_reg(ofs, boxes)
        nsize_loc = self.convert_to_imm(boxes[4])  # Negative for "signed"
        self.possibly_free_vars_for_op(op)
        res_loc = self.force_allocate_reg(op)
        return [base_loc, index_loc, ofs_loc, res_loc, nsize_loc]

    prepare_op_gc_load_indexed_i = _prepare_op_gc_load_indexed
    prepare_op_gc_load_indexed_r = _prepare_op_gc_load_indexed
    prepare_op_gc_load_indexed_f = _prepare_op_gc_load_indexed

    def _prepare_guard_arglocs(self, op):
        arglocs = [None] * (len(op.getfailargs()) + 1)
        arglocs[0] = ImmLocation(self.frame_manager.get_frame_depth())
        failargs = op.getfailargs()
        for i in range(len(failargs)):
            if failargs[i]:
                arglocs[i + 1] = self.loc(failargs[i])
        return arglocs

    def _prepare_op_guard_unary_op(self, op):
        boxes = op.getarglist()
        a0 = boxes[0]
        l0 = self.make_sure_var_in_reg(a0, boxes)

        # Note[#dont_free_vars]: Do not call `possibly_free_vars_for_op` or
        # `free_temp_vars` here because `_prepare_guard_arglocs` still need the
        # mapping between boxes and locations for `op.getfailargs()`.
        #
        # For example:
        #
        #    [i0, i1, i2]
        #    i3 = int_add(i0, i1)
        #    guard_value(i3, i2, descr=...) [i3]
        #    finish(descr=...)
        #
        # If we call `possibly_free_vars_for_op` here, `i3` will be freed, but
        # we still need it as failargs and the `self.loc(failargs[i])` in
        # `_prepare_guard_arglocs` will associate a random free frame slot,
        # which will result in incorrect result.
        #
        # Just don't call these two functions. The callsite in `assembler.py`
        # will call these two functions for us.

        guard_arglocs = self._prepare_guard_arglocs(op)
        return [l0] + guard_arglocs

    prepare_op_guard_true    = _prepare_op_guard_unary_op
    prepare_op_guard_false   = _prepare_op_guard_unary_op
    prepare_op_guard_nonnull = _prepare_op_guard_unary_op
    prepare_op_guard_isnull  = _prepare_op_guard_unary_op

    def prepare_op_guard_value(self, op):
        boxes = op.getarglist()
        a0, a1 = boxes
        l0 = self.make_sure_var_in_reg(a0, boxes)
        l1 = self.make_sure_var_in_reg(a1, boxes)
        # Note[#dont_free_vars]: Do not call `possibly_free_vars_for_op` or
        # `free_temp_vars`.
        return [l0, l1] + self._prepare_guard_arglocs(op)

    def _gen_prepare_guard_op_guard_bool_op(guard_true):
        def _prepare_guard_op_guard_bool_op(self, op, guard_op):
            boxes = op.getarglist()

            opnum = op.getopnum()
            if (opnum == rop.INT_EQ or opnum == rop.PTR_EQ or
                opnum == rop.INSTANCE_PTR_EQ):
                guard_branch_inst = COND_BEQ
            elif (opnum == rop.INT_NE or opnum == rop.PTR_NE or
                  opnum == rop.INSTANCE_PTR_NE):
                guard_branch_inst = COND_BNE
            elif opnum == rop.INT_LT:
                guard_branch_inst = COND_BLT
            elif opnum == rop.INT_LE:
                boxes = [boxes[1], boxes[0]]
                guard_branch_inst = COND_BGE
            elif opnum == rop.INT_GT:
                boxes = [boxes[1], boxes[0]]
                guard_branch_inst = COND_BLT
            elif opnum == rop.INT_GE:
                guard_branch_inst = COND_BGE
            elif opnum == rop.UINT_LT:
                guard_branch_inst = COND_BLTU
            elif opnum == rop.UINT_LE:
                if check_plus_one_imm_box(boxes[1]):
                    boxes = [boxes[0], ConstInt(boxes[1].getint() + 1)]
                    guard_branch_inst = COND_BLTU
                else:
                    boxes = [boxes[1], boxes[0]]
                    guard_branch_inst = COND_BGEU
            elif opnum == rop.UINT_GT:
                boxes = [boxes[1], boxes[0]]
                guard_branch_inst = COND_BLTU
            elif opnum == rop.UINT_GE:
                if check_plus_one_imm_box(boxes[0]):
                    boxes = [boxes[1], ConstInt(boxes[0].getint() + 1)]
                    guard_branch_inst = COND_BLTU
                else:
                    guard_branch_inst = COND_BGEU
            elif opnum == rop.INT_IS_ZERO:
                boxes = [boxes[0], ConstInt(0)]
                guard_branch_inst = COND_BEQ
            elif opnum == rop.INT_IS_TRUE:
                boxes = [boxes[0], ConstInt(0)]
                guard_branch_inst = COND_BNE
            else:
                assert False, 'unexpected case'

            locs = [self.make_sure_var_in_reg(v, boxes) for v in boxes]

            if not guard_true:
                guard_branch_inst = get_negated_branch_inst(guard_branch_inst)

            # Note[#dont_free_vars]: Do not call `possibly_free_vars_for_op` or
            # `free_temp_vars`.
            guard_arglocs = self._prepare_guard_arglocs(guard_op)

            arglocs = locs + guard_arglocs
            return arglocs, guard_branch_inst
        return _prepare_guard_op_guard_bool_op

    prepare_guard_op_guard_true  = _gen_prepare_guard_op_guard_bool_op(True)
    prepare_guard_op_guard_false = _gen_prepare_guard_op_guard_bool_op(False)

    def _gen_prepare_guard_op_guard_overflow_op(guard_overflow):
        def _prepare_guard_op_guard_overflow_op(self, op, guard_op):
            boxes = op.getarglist()

            # TODO: Optimize ADD/SUB with constant operands.

            # INT_ADD_OVF:
            #   add a2, a0, a1
            #   slt t0, a2, a0
            #   slti t1, a1, 0
            #   beq t0, t1, no_overflow
            # overflow:
            #   j ...
            # no_overflow:

            # INT_SUB_OVF:
            #   sub a2, a0, a1
            #   slt t0, a2, a0
            #   sgtz t1, a1
            #   beq t0, t1, no_overflow
            # overflow:
            #   j ...
            # no_overflow:

            # INT_MUL_OVF:
            #   mul a2, a0, a1
            #   mulh t0, a0, a1
            #   srai t1, a2, 63
            #   beq t0, t1, no_overflow
            # overflow:
            #   j ...
            # no_overflow:

            locs = [self.make_sure_var_in_reg(v, boxes) for v in boxes]
            # Note: Do not call `possibly_free_vars_for_op` or
            # `free_temp_vars`. The result register (a2) overlaps with the
            # lifetime of the arguments (a0/a1) and the lifetime of temporaries
            # (t0/t1).
            locs.append(self.force_allocate_reg(op, boxes))
            locs.append(self.rm.get_scratch_reg(INT, boxes + [op]))  # t0
            locs.append(self.rm.get_scratch_reg(INT, boxes + [op]))  # t1

            guard_branch_inst = COND_BNE if guard_overflow else COND_BEQ

            # Note[#dont_free_vars]: Do not call `possibly_free_vars_for_op` or
            # `free_temp_vars`.
            arglocs = locs + self._prepare_guard_arglocs(guard_op)
            return arglocs, guard_branch_inst
        return _prepare_guard_op_guard_overflow_op

    prepare_guard_op_guard_overflow = \
        _gen_prepare_guard_op_guard_overflow_op(True)
    prepare_guard_op_guard_no_overflow = \
        _gen_prepare_guard_op_guard_overflow_op(False)

    def prepare_op_guard_class(self, op):
        obj_loc = self.make_sure_var_in_reg(op.getarg(0))
        cls_loc = ImmLocation(rffi.cast(lltype.Signed, op.getarg(1).getint()))
        # Note[#dont_free_vars]: Do not call `possibly_free_vars_for_op` or
        # `free_temp_vars`.
        return [obj_loc, cls_loc] + self._prepare_guard_arglocs(op)

    prepare_op_guard_nonnull_class = prepare_op_guard_class

    prepare_op_guard_gc_type = prepare_op_guard_class
    prepare_op_guard_subclass = prepare_op_guard_class

    def prepare_op_guard_is_object(self, op):
        obj_loc = self.make_sure_var_in_reg(op.getarg(0))
        # Note[#dont_free_vars]: Do not call `possibly_free_vars_for_op` or
        # `free_temp_vars`.
        return [obj_loc] + self._prepare_guard_arglocs(op)

    def prepare_op_guard_not_invalidated(self, op):
        return self._prepare_guard_arglocs(op)

    def prepare_op_guard_exception(self, op):
        boxes = op.getarglist()

        expected_exc_tp_loc = self.make_sure_var_in_reg(boxes[0], boxes)
        if op in self.longevity and self.rm.stays_alive(op):
            res_exc_val_loc = self.force_allocate_reg(op, boxes)
        else:
            res_exc_val_loc = None

        arglocs = [expected_exc_tp_loc, res_exc_val_loc]
        return arglocs + self._prepare_guard_arglocs(op)

    def prepare_op_guard_no_exception(self, op):
        return self._prepare_guard_arglocs(op)  # Only failargs

    def prepare_op_save_exception(self, op):
        res = self.force_allocate_reg(op)
        return [res]

    prepare_op_save_exc_class = prepare_op_save_exception

    def prepare_op_restore_exception(self, op):
        boxes = op.getarglist()
        exc_tp_loc = self.make_sure_var_in_reg(boxes[0], boxes)
        exc_val_loc = self.make_sure_var_in_reg(boxes[1], boxes)
        return [exc_tp_loc, exc_val_loc]

    def prepare_op_check_memory_error(self, op):
        l0 = self.make_sure_var_in_reg(op.getarg(0))
        return [l0]

    def _prepare_op_same_as(self, op):
        boxes = op.getarglist()
        a0 = boxes[0]
        if check_imm_box(a0):
            l0 = self.convert_to_imm(a0)
        else:
            l0 = self.make_sure_var_in_reg(a0)
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op)
        return [l0, res]

    prepare_op_same_as_i = _prepare_op_same_as
    prepare_op_same_as_r = _prepare_op_same_as
    prepare_op_same_as_f = _prepare_op_same_as
    prepare_op_cast_ptr_to_int = _prepare_op_same_as
    prepare_op_cast_int_to_ptr = _prepare_op_same_as

    def _prepare_op_math_sqrt(self, op):
        # res = call_f(math_sqrt, arg1)
        l1 = self.make_sure_var_in_reg(op.getarg(1))
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op)
        return [l1, res]

    def _prepare_op_threadlocalref_get(self, op):
        # res = call_r(threadlocalref_get)
        res = self.force_allocate_reg(op)
        return [res]

    def before_call(self, force_store=[], save_all_regs=False):
        # Spill caller save registers.
        self.rm.before_call(force_store=force_store,
                            save_all_regs=save_all_regs)
        self.fprm.before_call(force_store=force_store,
                              save_all_regs=save_all_regs)

    def after_call(self, v):
        # Bind the return register to the variable `v`, which should hold the
        # returned value.
        if v.type == 'v':
            return
        if v.type == FLOAT:
            return self.fprm.after_call(v)
        else:
            return self.rm.after_call(v)

    def _call(self, op, gc_level):
        # Spill variables that need to be saved around calls:
        # gc_level == 0: callee cannot invoke the GC
        # gc_level == 1: can invoke GC, save all regs that contain pointers
        # gc_level == 2: can force, save all regs
        save_all_regs = gc_level == 2
        self.fprm.before_call(save_all_regs=save_all_regs)
        if gc_level == 1 and self.cpu.gc_ll_descr.gcrootmap:
            save_all_regs = 2
        self.rm.before_call(save_all_regs=save_all_regs)
        resloc = self.after_call(op)
        return resloc

    def _prepare_call(self, op, save_all_regs=False, first_arg_index=1):
        locs = [None] * (op.numargs() + 3)
        calldescr = op.getdescr()
        assert isinstance(calldescr, CallDescr)
        assert len(calldescr.arg_classes) == op.numargs() - first_arg_index

        for i in range(op.numargs()):
            locs[i + 3] = self.loc(op.getarg(i))

        size = calldescr.get_result_size()
        sign = calldescr.is_result_signed()
        sign_loc = ImmLocation(sign)
        locs[1] = ImmLocation(size)
        locs[2] = sign_loc

        effectinfo = calldescr.get_extra_info()
        if save_all_regs:
            gc_level = 2
        elif effectinfo is None or effectinfo.check_can_collect():
            gc_level = 1
        else:
            gc_level = 0

        locs[0] = self._call(op, gc_level)
        return locs

    def _prepare_op_call(self, op):
        calldescr = op.getdescr()
        assert calldescr is not None
        effectinfo = calldescr.get_extra_info()
        if effectinfo is not None:
            oopspecindex = effectinfo.oopspecindex
            if oopspecindex == EffectInfo.OS_MATH_SQRT:
                args = self._prepare_op_math_sqrt(op)
                self.assembler.math_sqrt(op, args)
                return
            elif oopspecindex == EffectInfo.OS_THREADLOCALREF_GET:
                args = self._prepare_op_threadlocalref_get(op)
                self.assembler.threadlocalref_get(op, args)
                return
        return self._prepare_call(op)

    prepare_op_call_i = _prepare_op_call
    prepare_op_call_f = _prepare_op_call
    prepare_op_call_r = _prepare_op_call
    prepare_op_call_n = _prepare_op_call

    def _prepare_op_cond_call(self, op):
        assert 2 <= op.numargs() <= 4 + 2

        func_addr = op.getarg(1)
        assert isinstance(func_addr, Const)

        # Allocate `r.x30` as a scratch reg because `cond_call_slowpath`
        # returns the result with `r.x30` and uses `r.x31` as a scratch
        # register internally.
        self.rm.get_scratch_reg(INT, selected_reg=r.x30)

        # Move function arguments to argument registers.
        _FUNC_ARGS = [r.x10, r.x11, r.x12, r.x13, r.x14, r.x15, r.x16, r.x17]
        allocated_arg_vars = []
        for i in range(2, op.numargs()):
            reg = _FUNC_ARGS[i - 2]
            arg = op.getarg(i)
            assert arg.type != FLOAT
            self.make_sure_var_in_reg(arg, allocated_arg_vars, selected_reg=reg)
            allocated_arg_vars.append(arg)

        # Move the `cond` variable to a register.
        argloc = self.make_sure_var_in_reg(op.getarg(0), allocated_arg_vars)

        if op.type == 'v':
            # A plain COND_CALL.  Calls the function when args[0] is true.
            # Often used just after a comparison operation.
            return [argloc]
        else:
            # COND_CALL_VALUE_I/R.  Calls the function when args[0] is equal to
            # 0 or NULL.  Returns the result from the function call if done, or
            # args[0] if it was not 0/NULL.  Implemented by forcing the result
            # to live in the same register as args[0], and overwriting it if we
            # really do the call.

            # Load the register for the result.  Possibly reuse 'args[0]'.  But
            # the old value of args[0], if it survives, is first spilled away.
            # We can't overwrite any of op.args[2:] here.
            args = op.getarglist()
            resloc = self.rm.force_result_in_reg(op, args[0],
                                                 forbidden_vars=args[2:])
            return [argloc, resloc]

    prepare_op_cond_call = _prepare_op_cond_call
    prepare_op_cond_call_value_i = _prepare_op_cond_call
    prepare_op_cond_call_value_r = _prepare_op_cond_call

    def prepare_guard_op_cond_call(self, cond_op, cond_call_op):
        # Allocate and emit `cond_op`.
        #
        # Note: We do this before `_prepare_op_cond_call` because
        # `_prepare_op_cond_call` may generate code to move register around.
        prepare_cond_op = regalloc_comp_operations[cond_op.getopnum()]
        cond_op_arglocs = prepare_cond_op(self, cond_op)
        asm_comp_operations[cond_op.getopnum()](self.assembler, cond_op,
                                                cond_op_arglocs)

        # Allocate registers for `cond_call_op`.
        op_arglocs = self._prepare_op_cond_call(cond_call_op)
        return (op_arglocs, COND_INVALID)

    def _prepare_op_cond_call_gc_wb(self, op):
        # Allocate an extra scratch register for `_write_barrier_fastpath`.
        tmplocs = [self.rm.get_scratch_reg(INT)]

        # We force all arguments in a reg because it will be needed anyway by
        # the following gc_store. It avoids loading it twice from the memory.
        args = op.getarglist()
        arglocs = [self.make_sure_var_in_reg(op.getarg(i), args)
                   for i in range(op.numargs())]
        return tmplocs + arglocs

    prepare_op_cond_call_gc_wb = _prepare_op_cond_call_gc_wb
    prepare_op_cond_call_gc_wb_array = _prepare_op_cond_call_gc_wb

    def prepare_guard_op_guard_not_forced(self, op, guard_op):
        if rop.is_call_release_gil(op.getopnum()):
            arglocs = self._prepare_call(op, save_all_regs=True,
                                         first_arg_index=2)
        elif rop.is_call_assembler(op.getopnum()):
            locs = self.locs_for_call_assembler(op)
            resloc = self._call(op, gc_level=2)
            arglocs = locs + [resloc]
        else:
            assert rop.is_call_may_force(op.getopnum())
            arglocs = self._prepare_call(op, save_all_regs=True)
        guard_arglocs = self._prepare_guard_arglocs(guard_op)
        return arglocs + guard_arglocs, len(arglocs)

    def prepare_op_guard_not_forced_2(self, op):
        self.rm.before_call(force_store=op.getfailargs(), save_all_regs=True)
        self.fprm.before_call(force_store=op.getfailargs(), save_all_regs=True)
        arglocs = self._prepare_guard_arglocs(op)
        return arglocs

    def prepare_op_call_malloc_nursery(self, op):
        size_box = op.getarg(0)
        assert isinstance(size_box, ConstInt)

        # Allocate registers for `malloc_slowpath`
        self.rm.get_scratch_reg(INT, selected_reg=r.x10)
        self.rm.get_scratch_reg(INT, selected_reg=r.x11)

        gcmap = self.get_gcmap([r.x10, r.x11])

        self.rm.free_temp_vars()
        self.rm.force_allocate_reg(op, selected_reg=r.x10)

        # Emit code for `malloc_nursery`.
        gc_ll_descr = self.cpu.gc_ll_descr
        self.assembler.malloc_cond(
            gc_ll_descr.get_nursery_free_addr(),
            gc_ll_descr.get_nursery_top_addr(), size_box.getint(), gcmap)

    def prepare_op_call_malloc_nursery_varsize_frame(self, op):
        size_box = op.getarg(0)
        assert not isinstance(size_box, ConstInt)  # We can't have a const here

        # Allocate registers for `malloc_slowpath`
        self.rm.get_scratch_reg(INT, selected_reg=r.x10)
        self.rm.get_scratch_reg(INT, selected_reg=r.x11)
        size_loc = self.rm.make_sure_var_in_reg(size_box)

        gcmap = self.get_gcmap([r.x10, r.x11])

        self.rm.possibly_free_vars_for_op(op)
        self.rm.free_temp_vars()
        self.rm.force_allocate_reg(op, selected_reg=r.x10)

        # Emit code for `malloc_nursery_varsize_frame`.
        gc_ll_descr = self.cpu.gc_ll_descr
        self.assembler.malloc_cond_varsize_frame(
            gc_ll_descr.get_nursery_free_addr(),
            gc_ll_descr.get_nursery_top_addr(), size_loc, gcmap)

    def prepare_op_call_malloc_nursery_varsize(self, op):
        # malloc_nursery_varsize(kind, itemsize, length)

        gc_ll_descr = self.cpu.gc_ll_descr
        if not hasattr(gc_ll_descr, 'max_size_of_young_obj'):
            raise Exception('unreachable code')
            # for boehm, this function should never be called

        arraydescr = op.getdescr()
        kind = op.getarg(0).getint()
        itemsize = op.getarg(1).getint()
        length_box = op.getarg(2)
        assert not isinstance(length_box, Const)

        # Allocate registers for `malloc_slowpath`
        self.rm.get_scratch_reg(INT, selected_reg=r.x10)
        self.rm.get_scratch_reg(INT, selected_reg=r.x11)
        if kind == rewrite.FLAG_ARRAY:
            self.rm.get_scratch_reg(INT, selected_reg=r.x12)

        length_loc = self.rm.make_sure_var_in_reg(length_box)

        if kind == rewrite.FLAG_ARRAY:
            gcmap = self.get_gcmap([r.x10, r.x11, r.x12])
        else:
            gcmap = self.get_gcmap([r.x10, r.x11])

        self.rm.possibly_free_vars_for_op(op)
        self.rm.free_temp_vars()
        self.rm.force_allocate_reg(op, selected_reg=r.x10)

        # Emit code for `malloc_nursery_varsize`.
        maxlength = (gc_ll_descr.max_size_of_young_obj - XLEN * 2) / itemsize
        self.assembler.malloc_cond_varsize(
            kind, gc_ll_descr.get_nursery_free_addr(),
            gc_ll_descr.get_nursery_top_addr(), length_loc, itemsize,
            maxlength, gcmap, arraydescr)

    def prepare_op_zero_array(self, op):
        # There are multiple implementations for `zero_array`. Leave the
        # register allocation to `opassembler.py`.
        return []

    def prepare_op_force_token(self, op):
        res = self.force_allocate_reg(op)
        return [res]

    def prepare_op_load_from_gc_table(self, op):
        res = self.force_allocate_reg(op)
        return [res]

    def prepare_op_enter_portal_frame(self, op):
        return []

    def prepare_op_leave_portal_frame(self, op):
        return []

    def prepare_op_keepalive(self, op):
        return []

    def prepare_op_jit_debug(self, op):
        return []

    def prepare_op_increment_debug_counter(self, op):
        boxes = op.getarglist()
        a0 = boxes[0]
        base_loc = self.make_sure_var_in_reg(a0, boxes)
        return [base_loc]

    def compute_hint_frame_locations(self, operations):
        # Fill in the `hint_frame_pos` dictionary of `frame_manager` based on
        # the JUMP at the end of the loop, by looking at where we would like
        # the boxes to be after the jump.
        #
        # Note: This is only an optimization.

        op = operations[-1]
        if op.getopnum() != rop.JUMP:
            return

        self.final_jump_op = op
        descr = op.getdescr()
        assert isinstance(descr, TargetToken)
        if descr._ll_loop_code != 0:
            # Set up `hint_frame_pos` if the target LABEL had been compiled
            # already, i.e. if it belongs to some already-compiled piece of
            # code.
            self._compute_hint_frame_locations_from_descr(descr)
        #else:
        #   The loop ends in a JUMP going back to a LABEL in the same loop.
        #   We cannot fill 'hint_frame_locations' immediately, but we can
        #   wait until the corresponding prepare_op_label() to know where the
        #   we would like the boxes to be after the jump.

    def _compute_hint_frame_locations_from_descr(self, descr):
        arglocs = descr._riscv_arglocs
        jump_op = self.final_jump_op
        assert len(arglocs) == jump_op.numargs()
        for i in range(jump_op.numargs()):
            box = jump_op.getarg(i)
            if not isinstance(box, Const):
                loc = arglocs[i]
                if loc is not None and loc.is_stack():
                    self.frame_manager.hint_frame_pos[box] = (
                        self.frame_manager.get_loc_index(loc))

    def prepare_op_label(self, op):
        descr = op.getdescr()
        assert isinstance(descr, TargetToken)
        inputargs = op.getarglist()
        arglocs = [None] * len(inputargs)

        # We use force_spill() on the boxes that are not going to be really
        # used any more in the loop, but they are kept alive anyway by being in
        # a next LABEL's or a JUMP's argument or fail_args of some guard
        position = self.rm.position
        for arg in inputargs:
            assert not isinstance(arg, Const)
            if self.longevity[arg].is_last_real_use_before(position):
                self.force_spill_var(arg)

        # Dissociate the register and stack slot because the jump op will copy
        # the updated value to the register and such value may be unrelated to
        # the stack slot. If the register is spilled by upcoming ops, we must
        # ensure the register is spilled to other stack slots instead of
        # overwriting to the old stack slot.
        for i in range(len(inputargs)):
            arg = inputargs[i]
            assert not isinstance(arg, Const)
            loc = self.loc(arg)
            arglocs[i] = loc
            if loc.is_core_reg() or loc.is_fp_reg():
                self.frame_manager.mark_as_free(arg)

        descr._riscv_arglocs = arglocs
        descr._riscv_clt = self.assembler.current_clt
        descr._ll_loop_code = self.assembler.mc.get_relative_pos()
        self.assembler.target_tokens_currently_compiling[descr] = None
        self.possibly_free_vars_for_op(op)

        # If the LABEL's descr is precisely the target of the JUMP at the end
        # of the same loop, i.e. if what we are compiling is a single loop that
        # ends up jumping to this LABEL, then we can now provide the hints
        # about the expected position of the spilled variables.
        jump_op = self.final_jump_op
        if jump_op is not None and jump_op.getdescr() is descr:
            self._compute_hint_frame_locations_from_descr(descr)
        return []

    def prepare_op_jump(self, op):
        assert self.jump_target_descr is None
        descr = op.getdescr()
        assert isinstance(descr, TargetToken)
        self.jump_target_descr = descr
        arglocs = descr._riscv_arglocs

        # If we are jumping to another loop/bridge, check the frame
        # depth before we jump.
        self.assembler.check_frame_depth_before_jump(self.jump_target_descr)

        # Core registers
        src_core_locs = []
        dst_core_locs = []
        scratch_core_reg = r.x31

        # Floating point registers
        src_fp_locs = []
        dst_fp_locs = []
        scratch_fp_reg = r.f31

        # Build the four lists
        for i in range(op.numargs()):
            box = op.getarg(i)
            src_loc = self.loc(box)
            dst_loc = arglocs[i]
            if box.type != FLOAT:
                src_core_locs.append(src_loc)
                dst_core_locs.append(dst_loc)
            else:
                src_fp_locs.append(src_loc)
                dst_fp_locs.append(dst_loc)

        remap_frame_layout_mixed(self.assembler, src_core_locs, dst_core_locs,
                                 scratch_core_reg, src_fp_locs, dst_fp_locs,
                                 scratch_fp_reg, XLEN)
        return []

    def prepare_op_finish(self, op):
        if op.numargs() == 1:
            loc = self.make_sure_var_in_reg(op.getarg(0))
            locs = [loc]
        else:
            locs = []
        return locs

    def loc(self, var):
        if var.type == FLOAT:
            return self.fprm.loc(var)
        else:
            return self.rm.loc(var)

    def make_sure_var_in_reg(self, var, forbidden_vars=[],
                             selected_reg=None, need_lower_byte=False):
        if var.type == FLOAT:
            return self.fprm.make_sure_var_in_reg(var, forbidden_vars,
                                                  selected_reg, need_lower_byte)
        else:
            return self.rm.make_sure_var_in_reg(var, forbidden_vars,
                                                selected_reg, need_lower_byte)

    def force_allocate_reg(self, var, forbidden_vars=[], selected_reg=None):
        if var.type == FLOAT:
            return self.fprm.force_allocate_reg(var, forbidden_vars,
                                                selected_reg)
        else:
            return self.rm.force_allocate_reg(var, forbidden_vars, selected_reg)

    def possibly_free_var(self, var):
        if var.type == FLOAT:
            self.fprm.possibly_free_var(var)
        else:
            self.rm.possibly_free_var(var)

    def possibly_free_vars_for_op(self, op):
        for i in range(op.numargs()):
            var = op.getarg(i)
            if var is not None:
                self.possibly_free_var(var)
        if op.is_guard():
            self.possibly_free_vars(op.getfailargs())

    def possibly_free_vars(self, vars):
        for var in vars:
            if var is not None:
                self.possibly_free_var(var)

    def force_spill_var(self, var):
        if var.type == FLOAT:
            self.fprm.force_spill_var(var)
        else:
            self.rm.force_spill_var(var)

    def free_temp_vars(self):
        self.rm.free_temp_vars()
        self.fprm.free_temp_vars()

    def _check_invariants(self):
        self.rm._check_invariants()
        self.fprm._check_invariants()

    def convert_to_imm(self, value):
        if isinstance(value, ConstInt):
            return self.rm.convert_to_imm(value)
        else:
            assert isinstance(value, ConstFloat)
            return self.fprm.convert_to_imm(value)

    def position(self):
        return self.rm.position

    def next_instruction(self):
        self.rm.next_instruction()
        self.fprm.next_instruction()

    def get_gcmap(self, forbidden_regs=[], noregs=False):
        frame_depth = self.frame_manager.get_frame_depth()
        gcmap = allocate_gcmap(self.assembler,
                               frame_depth, JITFRAME_FIXED_SIZE)
        for box, loc in self.rm.reg_bindings.iteritems():
            if loc in forbidden_regs:
                continue
            if box.type == REF and self.rm.is_still_alive(box):
                assert not noregs
                assert loc.is_core_reg()
                val = self.cpu.all_reg_indexes[loc.value]
                gcmap[val // XLEN // 8] |= r_uint(1) << (val % (XLEN * 8))
        for box, loc in self.frame_manager.bindings.iteritems():
            if box.type == REF and self.rm.is_still_alive(box):
                assert loc.is_stack()
                val = loc.position + JITFRAME_FIXED_SIZE
                gcmap[val // XLEN // 8] |= r_uint(1) << (val % (XLEN * 8))
        return gcmap

    def get_final_frame_depth(self):
        return self.frame_manager.get_frame_depth()


def not_implemented(self, op):
    llop.debug_print(lltype.Void,
                     '[riscv/regalloc] %s not implemented' % op.getopname())
    raise NotImplementedError(op)

def not_implemented_guard_op(self, op, prevop):
    llop.debug_print(lltype.Void,
                     '[riscv/regalloc] %s not implemented' % op.getopname())
    raise NotImplementedError(op)

def not_implemented_comp_op(self, op):
    llop.debug_print(lltype.Void,
                     '[riscv/regalloc] %s not implemented' % op.getopname())
    raise NotImplementedError(op)

regalloc_operations = [not_implemented] * (rop._LAST + 1)
regalloc_guard_operations = [not_implemented_guard_op] * (rop._LAST + 1)
regalloc_comp_operations = [not_implemented_comp_op] * (rop._LAST + 1)

for key, value in rop.__dict__.items():
    key = key.lower()
    if key.startswith('_'):
        continue
    method_name = 'prepare_op_%s' % key
    if hasattr(Regalloc, method_name):
        func = getattr(Regalloc, method_name).im_func
        regalloc_operations[value] = func
    method_name = 'prepare_guard_op_%s' % key
    if hasattr(Regalloc, method_name):
        func = getattr(Regalloc, method_name).im_func
        regalloc_guard_operations[value] = func
    method_name = 'prepare_comp_op_%s' % key
    if hasattr(Regalloc, method_name):
        func = getattr(Regalloc, method_name).im_func
        regalloc_comp_operations[value] = func

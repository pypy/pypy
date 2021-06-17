#!/usr/bin/env python

from rpython.jit.backend.llsupport.regalloc import (
    BaseRegalloc, FrameManager, RegisterManager, TempVar,
    compute_vars_longevity)
from rpython.jit.backend.riscv import registers as r
from rpython.jit.backend.riscv.arch import (SINT12_IMM_MAX, SINT12_IMM_MIN)
from rpython.jit.backend.riscv.locations import (
    ConstFloatLoc, ImmLocation, StackLocation, get_fp_offset)
from rpython.jit.codewriter import longlong
from rpython.jit.metainterp.history import (
    Const, ConstFloat, ConstInt, ConstPtr, FLOAT, INT, REF)
from rpython.jit.metainterp.resoperation import rop
from rpython.rtyper.lltypesystem import lltype, rffi


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
        if isinstance(c, ConstInt):
            val = rffi.cast(lltype.Signed, c.value)
            return ImmLocation(val)
        raise NotImplementedError('imm type not supported')

    def return_constant(self, v, forbidden_vars=[], selected_reg=None):
        self._check_type(v)
        if isinstance(v, Const):
            if isinstance(v, ConstInt):
                reg_type = INT
            else:
                assert isinstance(v, ConstPtr)
                reg_type = REF

            if v.value == 0 and selected_reg is None:
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
        adr = self.assembler.datablockwrapper.malloc_aligned(8, 8)
        x = c.getfloatstorage()
        rffi.cast(rffi.CArrayPtr(longlong.FLOATSTORAGE), adr)[0] = x
        return ConstFloatLoc(adr)

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


def check_imm_arg(imm):
    return imm >= SINT12_IMM_MIN and imm <= SINT12_IMM_MAX

def check_imm_box(arg):
    if isinstance(arg, ConstInt):
        return check_imm_arg(arg.getint())
    return False

def check_negative_imm_box(arg):
    if isinstance(arg, ConstInt):
        return check_imm_arg(-arg.getint())
    return False


class Regalloc(BaseRegalloc):
    def __init__(self, assembler):
        self.cpu = assembler.cpu
        self.assembler = assembler
        self.frame_manager = None
        self.rm = None
        self.fprm = None
        #self.jump_target_descr = None
        #self.final_jump_op = None

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

    def prepare_op_int_add(self, op):
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

    def prepare_op_float_add(self, op):
        boxes = op.getarglist()
        a0, a1 = boxes
        l0 = self.make_sure_var_in_reg(a0, boxes)
        l1 = self.make_sure_var_in_reg(a1, boxes)
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op)
        return [l0, l1, res]

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

    def get_final_frame_depth(self):
        return self.frame_manager.get_frame_depth()


def not_implemented(self, op):
    print '[riscv/regalloc] %s not implemented' % op.getopname()
    raise NotImplementedError(op)

def not_implemented_guard_op(self, op, prevop):
    print '[riscv/regalloc] %s not implemented' % op.getopname()
    raise NotImplementedError(op)

def not_implemented_comp_op(self, op):
    print '[riscv/regalloc] %s not implemented' % op.getopname()
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

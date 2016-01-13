from rpython.jit.metainterp.history import ConstInt, FLOAT, Const
from rpython.jit.backend.zarch.locations import imm, addr
from rpython.jit.backend.llsupport.regalloc import TempVar
import rpython.jit.backend.zarch.registers as r

def check_imm_value(value, lower_bound=-2**15, upper_bound=2**15-1):
    return lower_bound <= value <= upper_bound

def check_imm(arg, lower_bound=-2**15, upper_bound=2**15-1):
    if isinstance(arg, ConstInt):
        i = arg.getint()
        return lower_bound <= i <= upper_bound
    return False

def check_imm32(arg):
    return check_imm(arg, -2**31, 2**31-1)

def check_imm20(arg):
    return check_imm(arg, -2**19, 2**19-1)

def prepare_int_add(self, op):
    a0 = op.getarg(0)
    a1 = op.getarg(1)
    if check_imm32(a0):
        a0, a1 = a1, a0
    l0 = self.ensure_reg(a0)
    if check_imm32(a1):
        l1 = imm(a1.getint())
    else:
        l1 = self.ensure_reg(a1)
    self.force_result_in_reg(op, a0)
    self.free_op_vars()
    return [l0, l1]

def prepare_int_mul(self, op):
    a0 = op.getarg(0)
    a1 = op.getarg(1)
    if check_imm32(a0):
        a0, a1 = a1, a0
    l0 = self.ensure_reg(a0)
    if check_imm32(a1):
        l1 = imm(a1.getint())
    else:
        l1 = self.ensure_reg(a1)
    self.force_result_in_reg(op, a0)
    self.free_op_vars()
    return [l0, l1]

def prepare_int_mul_ovf(self, op):
    a0 = op.getarg(0)
    a1 = op.getarg(1)
    if check_imm32(a0):
        a0, a1 = a1, a0
    lr,lq = self.rm.ensure_even_odd_pair(a0, op, bind_first=False)
    if check_imm32(a1):
        l1 = imm(a1.getint())
    else:
        l1 = self.ensure_reg(a1)
    self.free_op_vars()
    return [lr, lq, l1]

def generate_div_mod(modulus):
    def f(self, op):
        a0 = op.getarg(0)
        a1 = op.getarg(1)
        if isinstance(a0, Const):
            poolloc = self.ensure_reg(a0)
            lr,lq = self.rm.ensure_even_odd_pair(a0, op, bind_first=modulus, must_exist=False)
            self.assembler.mc.LG(lq, poolloc)
        else:
            lr,lq = self.rm.ensure_even_odd_pair(a0, op, bind_first=modulus)
        l1 = self.ensure_reg(a1)
        self.free_op_vars()
        self.rm._check_invariants()
        return [lr, lq, l1]
    return f

prepare_int_div = generate_div_mod(False)
prepare_int_mod = generate_div_mod(True)

def prepare_int_sub(self, op):
    a0 = op.getarg(0)
    a1 = op.getarg(1)
    # sub is not commotative, thus cannot swap operands
    l1 = self.ensure_reg(a1)
    l0 = self.ensure_reg(a0)
    if isinstance(a0, Const):
        loc = self.force_allocate_reg(op)
        self.assembler.mc.LG(loc, l0)
        l0 = loc
    else:
        self.rm.force_result_in_reg(op, a0)
    self.free_op_vars()
    return [l0, l1]

def prepare_int_logic(self, op):
    a0 = op.getarg(0)
    a1 = op.getarg(1)
    if isinstance(a0, ConstInt):
        a0, a1 = a1, a0
    l0 = self.ensure_reg(a0)
    l1 = self.ensure_reg(a1)
    self.force_result_in_reg(op, a0)
    self.free_op_vars()
    return [l0, l1]

def prepare_int_shift(self, op):
    a0 = op.getarg(0)
    a1 = op.getarg(1)
    if isinstance(a1, ConstInt):
        # note that the shift value is stored
        # in the addr part of the instruction
        l1 = addr(a1.getint())
    else:
        tmp = self.rm.ensure_reg(a1, force_in_reg=True)
        l1 = addr(0, tmp)
    l0 = self.ensure_reg(a0, force_in_reg=True)
    lr = self.force_allocate_reg(op)
    self.free_op_vars()
    return [lr, l0, l1]

def generate_cmp_op(signed=True):
    def prepare_cmp_op(self, op):
        a0 = op.getarg(0)
        a1 = op.getarg(1)
        invert = imm(0)
        l0 = self.ensure_reg(a0)
        if signed and check_imm32(a1):
            l1 = imm(a1.getint())
        else:
            l1 = self.ensure_reg(a1)
        if l0.is_in_pool():
            poolloc = l0
            l0 = self.force_allocate_reg(op)
            self.assembler.mc.LG(l0, poolloc)
        res = self.force_allocate_reg_or_cc(op)
        #self.force_result_in_reg(op, a0)
        self.free_op_vars()
        return [l0, l1, res, invert]
    return prepare_cmp_op

def prepare_float_cmp_op(self, op):
    l0 = self.ensure_reg(op.getarg(0), force_in_reg=True)
    l1 = self.ensure_reg(op.getarg(1))
    res = self.force_allocate_reg_or_cc(op)
    self.free_op_vars()
    return [l0, l1, res]

def prepare_binary_op(self, op):
    a0 = op.getarg(0)
    a1 = op.getarg(1)
    l0 = self.ensure_reg(a0)
    l1 = self.ensure_reg(a1)
    self.force_result_in_reg(op, a0)
    self.free_op_vars()
    return [l0, l1]

def generate_prepare_float_binary_op(allow_swap=False):
    def prepare_float_binary_op(self, op):
        a0 = op.getarg(0)
        a1 = op.getarg(1)
        if allow_swap:
            if isinstance(a0, Const):
                a0,a1 = a1,a0
        l0 = self.ensure_reg(a0)
        l1 = self.ensure_reg(a1)
        if isinstance(a0, Const):
            newloc = self.force_allocate_reg(op)
            self.assembler.regalloc_mov(l0, newloc)
            l0 = newloc
        else:
            self.force_result_in_reg(op, a0)
        self.free_op_vars()
        return [l0, l1]
    return prepare_float_binary_op

def prepare_unary_cmp(self, op):
    a0 = op.getarg(0)
    assert not isinstance(a0, ConstInt)
    l0 = self.ensure_reg(a0)
    self.force_result_in_reg(op, a0)
    res = self.force_allocate_reg_or_cc(op)
    self.free_op_vars()
    return [l0, res]

def prepare_unary_op(self, op):
    a0 = op.getarg(0)
    assert not isinstance(a0, ConstInt)
    l0 = self.ensure_reg(a0, force_in_reg=True)
    res = self.force_result_in_reg(op, a0)
    self.free_op_vars()
    return [l0,]

def prepare_same_as(self, op):
    a0 = op.getarg(0)
    l0 = self.ensure_reg(a0)
    res = self.force_allocate_reg(op)
    self.free_op_vars()
    return [l0, res]

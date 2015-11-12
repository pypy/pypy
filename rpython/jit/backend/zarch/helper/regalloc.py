from rpython.jit.metainterp.history import ConstInt, FLOAT
from rpython.jit.backend.zarch.locations import imm, addr

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

def prepare_int_div(self, op):
    a0 = op.getarg(0)
    a1 = op.getarg(1)
    lr,lq = self.rm.ensure_even_odd_pair(a0, bind_first=False)
    l1 = self.ensure_reg(a1)
    self.rm.force_result_in_reg(op, a0)
    self.free_op_vars()
    return [lr, lq, l1]

def prepare_int_mod(self, op):
    a0 = op.getarg(0)
    a1 = op.getarg(1)
    lr,lq = self.rm.ensure_even_odd_pair(a0, bind_first=True)
    l1 = self.ensure_reg(a1)
    self.rm.force_result_in_reg(op, a0)
    self.free_op_vars()
    return [lr, lq, l1]

def prepare_int_sub(self, op):
    a0 = op.getarg(0)
    a1 = op.getarg(1)
    if isinstance(a0, ConstInt):
        a0, a1 = a1, a0
    l0 = self.ensure_reg(a0)
    l1 = self.ensure_reg(a1)
    self.force_result_in_reg(op, a0)
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
    assert isinstance(a1, ConstInt)
    l1 = self.ensure_reg(a1)
    assert check_imm20(a1)
    l0 = self.ensure_reg(a0)
    # note that the shift value is stored
    # in the addr part of the instruction
    l1 = addr(a1.getint())
    self.force_result_in_reg(op, a0)
    self.free_op_vars()
    return [l0, l1]

def prepare_cmp_op(self, op):
    a0 = op.getarg(0)
    a1 = op.getarg(1)
    if check_imm(a0):
        a0, a1 = a1, a0
    l0 = self.ensure_reg(a0)
    if check_imm(a1):
        l1 = imm(a1.getint())
    else:
        l1 = self.ensure_reg(a1)
    self.force_result_in_reg(op, a0)
    self.free_op_vars()
    return [l0, l1]

def prepare_binary_op(self, op):
    a0 = op.getarg(0)
    a1 = op.getarg(1)
    l0 = self.ensure_reg(a0)
    l1 = self.ensure_reg(a1)
    self.force_result_in_reg(op, a0)
    self.free_op_vars()
    return [l0, l1]

def prepare_unary_op(self, op):
    a0 = op.getarg(0)
    assert not isinstance(a0, ConstInt)
    l0 = self.ensure_reg(a0)
    self.force_result_in_reg(op, a0)
    self.free_op_vars()
    return [l0]

from pypy.jit.metainterp.history import ConstInt
from pypy.rlib.objectmodel import we_are_translated
from pypy.jit.metainterp.history import Box

IMM_SIZE = 2 ** 15 - 1

def check_imm_box(arg, size=IMM_SIZE, allow_zero=True):
    if isinstance(arg, ConstInt):
        return _check_imm_arg(arg.getint(), size, allow_zero)
    return False

def _check_imm_arg(arg, size=IMM_SIZE, allow_zero=True):
    #assert not isinstance(arg, ConstInt)
    #if not we_are_translated():
    #    if not isinstance(arg, int):
    #        import pdb; pdb.set_trace()
    i = arg
    if allow_zero:
        lower_bound = i >= 0
    else:
        lower_bound = i > 0
    return i <= size and lower_bound

def prepare_cmp_op():
    def f(self, op):
        boxes = op.getarglist()
        arg0, arg1 = boxes
        imm_a0 = _check_imm_arg(arg0)
        imm_a1 = _check_imm_arg(arg1)
        l0 = self._ensure_value_is_boxed(arg0, forbidden_vars=boxes)

        if imm_a1 and not imm_a0:
            l1 = self.make_sure_var_in_reg(arg1, boxes)
        else:
            l1 = self._ensure_value_is_boxed(arg1, forbidden_vars=boxes)

        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op.result)
        return [l0, l1, res]
    return f

def prepare_unary_cmp():
    def f(self, op):
        a0 = op.getarg(0)
        assert isinstance(a0, Box)
        reg = self.make_sure_var_in_reg(a0)
        self.possibly_free_vars_for_op(op)
        res = self.force_allocate_reg(op.result, [a0])
        return [reg, res]
    return f

def prepare_unary_int_op():
    def f(self, op):
        l0 = self._ensure_value_is_boxed(op.getarg(0))
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op.result)
        return [l0, res]
    return f

def prepare_binary_int_op_with_imm():
    def f(self, op):
        boxes = op.getarglist()
        b0, b1 = boxes
        imm_b0 = _check_imm_arg(b0)
        imm_b1 = _check_imm_arg(b1)
        if not imm_b0 and imm_b1:
            l0 = self._ensure_value_is_boxed(b0)
            l1 = self.make_sure_var_in_reg(b1, boxes)
        elif imm_b0 and not imm_b1:
            l0 = self.make_sure_var_in_reg(b0)
            l1 = self._ensure_value_is_boxed(b1, boxes)
        else:
            l0 = self._ensure_value_is_boxed(b0)
            l1 = self._ensure_value_is_boxed(b1, boxes)
        locs = [l0, l1]
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op.result)
        return locs + [res]
    return f

def prepare_binary_int_op():
    def f(self, op):
        boxes = list(op.getarglist())
        b0, b1 = boxes

        reg1 = self._ensure_value_is_boxed(b0, forbidden_vars=boxes)
        reg2 = self._ensure_value_is_boxed(b1, forbidden_vars=boxes)

        self.possibly_free_vars_for_op(op)
        res = self.force_allocate_reg(op.result)
        self.possibly_free_var(op.result)
        return [reg1, reg2, res]
    return f

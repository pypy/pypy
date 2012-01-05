from pypy.jit.metainterp.history import ConstInt
from pypy.rlib.objectmodel import we_are_translated

def _check_imm_arg(arg, size=0xFF, allow_zero=True):
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
        l0, box = self._ensure_value_is_boxed(arg0, forbidden_vars=boxes)
        boxes.append(box)
        if imm_a1 and not imm_a0:
            l1 = self.make_sure_var_in_reg(arg1, boxes)
        else:
            l1, box = self._ensure_value_is_boxed(arg1, forbidden_vars=boxes)
            boxes.append(box)
        self.possibly_free_vars(boxes)
        res = self.force_allocate_reg(op.result)
        self.possibly_free_var(op.result)
        return [l0, l1, res]
    return f

def prepare_unary_cmp():
    def f(self, op):
        a0 = op.getarg(0)
        reg, box = self._ensure_value_is_boxed(a0)
        res = self.force_allocate_reg(op.result, [box])
        self.possibly_free_vars([a0, box, op.result])
        return [reg, res]
    return f

def prepare_unary_int_op():
    def f(self, op):
        l0, box = self._ensure_value_is_boxed(op.getarg(0))
        self.possibly_free_var(box)
        res = self.force_allocate_reg(op.result)
        self.possibly_free_var(op.result)
        return [l0, res]
    return f

def prepare_binary_int_op_with_imm():
    def f(self, op):
        boxes = op.getarglist()
        b0, b1 = boxes
        imm_b0 = _check_imm_arg(b0)
        imm_b1 = _check_imm_arg(b1)
        if not imm_b0 and imm_b1:
            l0, box = self._ensure_value_is_boxed(b0)
            l1 = self.make_sure_var_in_reg(b1, [b0])
            boxes.append(box)
        elif imm_b0 and not imm_b1:
            l0 = self.make_sure_var_in_reg(b0)
            l1, box = self._ensure_value_is_boxed(b1, [b0])
            boxes.append(box)
        else:
            l0, box = self._ensure_value_is_boxed(b0)
            boxes.append(box)
            l1, box = self._ensure_value_is_boxed(b1, [box])
            boxes.append(box)
        locs = [l0, l1]
        self.possibly_free_vars(boxes)
        res = self.force_allocate_reg(op.result)
        return locs + [res]
    return f

def prepare_binary_int_op():
    def f(self, op):
        boxes = list(op.getarglist())
        b0, b1 = boxes

        reg1, box = self._ensure_value_is_boxed(b0, forbidden_vars=boxes)
        boxes.append(box)
        reg2, box = self._ensure_value_is_boxed(b1, forbidden_vars=boxes)
        boxes.append(box)

        self.possibly_free_vars(boxes)
        self.possibly_free_vars_for_op(op)
        res = self.force_allocate_reg(op.result)
        self.possibly_free_var(op.result)
        return [reg1, reg2, res]
    return f

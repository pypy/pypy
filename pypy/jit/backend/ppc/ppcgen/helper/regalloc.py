from pypy.jit.metainterp.history import ConstInt

def _check_imm_arg(arg):
    return isinstance(arg, ConstInt)

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

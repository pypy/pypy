from pypy.jit.backend.arm import conditions as c
from pypy.jit.backend.arm import registers as r
from pypy.jit.backend.arm.codebuilder import AbstractARMv7Builder
from pypy.jit.metainterp.history import ConstInt, BoxInt, Box, FLOAT
from pypy.jit.metainterp.history import ConstInt

# XXX create a version that does not need a ConstInt
def _check_imm_arg(arg, size=0xFF, allow_zero=True):
    if isinstance(arg, ConstInt):
        i = arg.getint()
        if allow_zero:
            lower_bound = i >= 0
        else:
            lower_bound = i > 0
        return i <= size and lower_bound
    return False

def prepare_op_ri(name=None, imm_size=0xFF, commutative=True, allow_zero=True):
    def f(self, op, fcond):
        assert fcond is not None
        a0 = op.getarg(0)
        a1 = op.getarg(1)
        boxes = list(op.getarglist())
        imm_a0 = _check_imm_arg(a0, imm_size, allow_zero=allow_zero)
        imm_a1 = _check_imm_arg(a1, imm_size, allow_zero=allow_zero)
        if not imm_a0 and imm_a1:
            l0, box = self._ensure_value_is_boxed(a0)
            boxes.append(box)
            l1 = self.make_sure_var_in_reg(a1, boxes)
        elif commutative and imm_a0 and not imm_a1:
            l1 = self.make_sure_var_in_reg(a0, boxes)
            l0, box = self._ensure_value_is_boxed(a1, boxes)
            boxes.append(box)
        else:
            l0, box = self._ensure_value_is_boxed(a0, boxes)
            boxes.append(box)
            l1, box = self._ensure_value_is_boxed(a1, boxes)
            boxes.append(box)
        self.possibly_free_vars(boxes)
        res = self.force_allocate_reg(op.result, boxes)
        self.possibly_free_var(op.result)
        return [l0, l1, res]
    if name:
        f.__name__ = name
    return f

def prepare_float_op(name=None, base=True, float_result=True, guard=False):
    if guard:
        def f(self, op, guard_op, fcond):
            locs = []
            loc1, box1 = self._ensure_value_is_boxed(op.getarg(0))
            locs.append(loc1)
            if base:
                loc2, box2 = self._ensure_value_is_boxed(op.getarg(1))
                locs.append(loc2)
                self.possibly_free_var(box2)
            self.possibly_free_var(box1)
            if guard_op is None:
                res = self.force_allocate_reg(op.result)
                assert float_result == (op.result.type == FLOAT)
                self.possibly_free_var(op.result)
                locs.append(res)
                return locs
            else:
                args = self._prepare_guard(guard_op, locs)
                self.possibly_free_vars(guard_op.getfailargs())
                return args
    else:
        def f(self, op, fcond):
            locs = []
            loc1, box1 = self._ensure_value_is_boxed(op.getarg(0))
            locs.append(loc1)
            if base:
                loc2, box2 = self._ensure_value_is_boxed(op.getarg(1))
                locs.append(loc2)
                self.possibly_free_var(box2)
            self.possibly_free_var(box1)
            res = self.force_allocate_reg(op.result)
            assert float_result == (op.result.type == FLOAT)
            self.possibly_free_var(op.result)
            locs.append(res)
            return locs
    if name:
        f.__name__ = name
    return f

def prepare_op_by_helper_call(name):
    def f(self, op, fcond):
        assert fcond is not None
        a0 = op.getarg(0)
        a1 = op.getarg(1)
        arg1 = self.make_sure_var_in_reg(a0, selected_reg=r.r0)
        arg2 = self.make_sure_var_in_reg(a1, selected_reg=r.r1)
        assert arg1 == r.r0
        assert arg2 == r.r1
        if isinstance(a0, Box) and self.stays_alive(a0):
            self.force_spill_var(a0)
        self.possibly_free_var(a0)
        self.after_call(op.result)
        self.possibly_free_var(a1)
        self.possibly_free_var(op.result)
        return []
    f.__name__ = name
    return f

def prepare_cmp_op(name=None):
    def f(self, op, guard_op, fcond):
        assert fcond is not None
        boxes = list(op.getarglist())
        if not inverse:
            arg0, arg1 = boxes
        else:
            arg1, arg0 = boxes
        # XXX consider swapping argumentes if arg0 is const
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
        if guard_op is None:
            res = self.force_allocate_reg(op.result)
            self.possibly_free_var(op.result)
            return [l0, l1, res]
        else:
            args = self._prepare_guard(guard_op, [l0, l1])
            self.possibly_free_vars(guard_op.getfailargs())
            return args
    if name:
        f.__name__ = name
    return f

def prepare_op_unary_cmp(name=None):
    def f(self, op, guard_op, fcond):
        assert fcond is not None
        a0 = op.getarg(0)
        reg, box = self._ensure_value_is_boxed(a0)
        if guard_op is None:
            res = self.force_allocate_reg(op.result, [box])
            self.possibly_free_vars([a0, box, op.result])
            return [reg, res]
        else:
            args = self._prepare_guard(guard_op, [reg])
            self.possibly_free_vars(guard_op.getfailargs())
            return args
    if name:
        f.__name__ = name
    return f

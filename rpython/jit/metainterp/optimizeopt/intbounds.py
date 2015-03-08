import sys
from rpython.jit.metainterp.history import ConstInt
from rpython.jit.metainterp.optimize import InvalidLoop
from rpython.jit.metainterp.optimizeopt.intutils import (IntBound,
    IntLowerBound, IntUpperBound)
from rpython.jit.metainterp.optimizeopt.optimizer import (Optimization, CONST_1,
    CONST_0)
from rpython.jit.metainterp.optimizeopt.info import MODE_ARRAY, MODE_STR,\
     MODE_UNICODE
from rpython.jit.metainterp.optimizeopt.util import make_dispatcher_method
from rpython.jit.metainterp.resoperation import rop, AbstractResOp


def get_integer_min(is_unsigned, byte_size):
    if is_unsigned:
        return 0
    else:
        return -(1 << ((byte_size << 3) - 1))


def get_integer_max(is_unsigned, byte_size):
    if is_unsigned:
        return (1 << (byte_size << 3)) - 1
    else:
        return (1 << ((byte_size << 3) - 1)) - 1


IS_64_BIT = sys.maxint > 2**32

def next_pow2_m1(n):
    """Calculate next power of 2 greater than n minus one."""
    n |= n >> 1
    n |= n >> 2
    n |= n >> 4
    n |= n >> 8
    n |= n >> 16
    if IS_64_BIT:
        n |= n >> 32
    return n


class OptIntBounds(Optimization):
    """Keeps track of the bounds placed on integers by guards and remove
       redundant guards"""

    def propagate_forward(self, op):
        dispatch_opt(self, op)

    def opt_default(self, op):
        assert not op.is_ovf()
        self.emit_operation(op)

    def propagate_bounds_backward(self, box):
        # FIXME: This takes care of the instruction where box is the reuslt
        #        but the bounds produced by all instructions where box is
        #        an argument might also be tighten
        b = self.getintbound(box)
        if b.has_lower and b.has_upper and b.lower == b.upper:
            self.make_constant_int(box, b.lower)

        if isinstance(box, AbstractResOp):
            dispatch_bounds_ops(self, box)

    def _optimize_guard_true_false_value(self, op):
        self.emit_operation(op)
        if op.getarg(0).type == 'i':
            self.propagate_bounds_backward(op.getarg(0))

    optimize_GUARD_TRUE = _optimize_guard_true_false_value
    optimize_GUARD_FALSE = _optimize_guard_true_false_value
    optimize_GUARD_VALUE = _optimize_guard_true_false_value

    def optimize_INT_OR_or_XOR(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        if v1.box is v2.box:
            if op.getopnum() == rop.INT_OR:
                self.make_equal_to(op, v1)
            else:
                self.make_constant_int(op, 0)
            return
        self.emit_operation(op)
        bound1 = v1.getintbound()
        bound2 = v2.getintbound()
        if bound1.known_ge(IntBound(0, 0)) and \
           bound2.known_ge(IntBound(0, 0)):
            r = self.getvalue(op).getintbound()
            mostsignificant = bound1.upper | bound2.upper
            r.intersect(IntBound(0, next_pow2_m1(mostsignificant)))

    optimize_INT_OR = optimize_INT_OR_or_XOR
    optimize_INT_XOR = optimize_INT_OR_or_XOR

    def optimize_INT_AND(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        self.emit_operation(op)

        r = self.getvalue(op)
        if v2.is_constant():
            val = v2.box.getint()
            if val >= 0:
                r.getintbound().intersect(IntBound(0, val))
        elif v1.is_constant():
            val = v1.box.getint()
            if val >= 0:
                r.getintbound().intersect(IntBound(0, val))
        elif v1.getintbound().known_ge(IntBound(0, 0)) and \
          v2.getintbound().known_ge(IntBound(0, 0)):
            lesser = min(v1.getintbound().upper, v2.getintbound().upper)
            r.getintbound().intersect(IntBound(0, next_pow2_m1(lesser)))

    def optimize_INT_SUB(self, op):
        self.emit_operation(op)
        b1 = self.getintbound(op.getarg(0))
        b2 = self.getintbound(op.getarg(1))
        b = b1.sub_bound(b2)
        if b.bounded():
            self.getintbound(op).intersect(b)

    def optimize_INT_ADD(self, op):
        self.emit_operation(op)
        b1 = self.getintbound(op.getarg(0))
        b2 = self.getintbound(op.getarg(1))
        r = self.getintbound(op)
        b = b1.add_bound(b2)
        if b.bounded():
            r.intersect(b)

    def optimize_INT_MUL(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        self.emit_operation(op)
        r = self.getvalue(op)
        b = v1.getintbound().mul_bound(v2.getintbound())
        if b.bounded():
            r.getintbound().intersect(b)

    def optimize_INT_FLOORDIV(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        self.emit_operation(op)
        r = self.getvalue(op)
        r.getintbound().intersect(v1.getintbound().div_bound(v2.getintbound()))

    def optimize_INT_MOD(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        known_nonneg = (v1.getintbound().known_ge(IntBound(0, 0)) and
                        v2.getintbound().known_ge(IntBound(0, 0)))
        if known_nonneg and v2.is_constant():
            val = v2.box.getint()
            if (val & (val-1)) == 0:
                # nonneg % power-of-two ==> nonneg & (power-of-two - 1)
                arg1 = op.getarg(0)
                arg2 = ConstInt(val-1)
                op = self.replace_op_with(op, rop.INT_AND,
                                          args=[arg1, arg2])
        self.emit_operation(op)
        if v2.is_constant():
            val = v2.box.getint()
            r = self.getvalue(op)
            if val < 0:
                if val == -sys.maxint-1:
                    return     # give up
                val = -val
            if known_nonneg:
                r.getintbound().make_ge(IntBound(0, 0))
            else:
                r.getintbound().make_gt(IntBound(-val, -val))
            r.getintbound().make_lt(IntBound(val, val))

    def optimize_INT_LSHIFT(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        self.emit_operation(op)
        r = self.getvalue(op)
        b = v1.getintbound().lshift_bound(v2.getintbound())
        r.getintbound().intersect(b)
        # intbound.lshift_bound checks for an overflow and if the
        # lshift can be proven not to overflow sets b.has_upper and
        # b.has_lower
        if b.has_lower and b.has_upper:
            # Synthesize the reverse op for optimize_default to reuse
            self.pure(rop.INT_RSHIFT, [op, op.getarg(1)], op.getarg(0))

    def optimize_INT_RSHIFT(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        b = v1.getintbound().rshift_bound(v2.getintbound())
        if b.has_lower and b.has_upper and b.lower == b.upper:
            # constant result (likely 0, for rshifts that kill all bits)
            self.make_constant_int(op, b.lower)
        else:
            self.emit_operation(op)
            r = self.getvalue(op)
            r.getintbound().intersect(b)

    def optimize_GUARD_NO_OVERFLOW(self, op):
        lastop = self.last_emitted_operation
        if lastop is not None:
            opnum = lastop.getopnum()
            args = lastop.getarglist()
            result = lastop
            # If the INT_xxx_OVF was replaced with INT_xxx or removed
            # completely, then we can kill the GUARD_NO_OVERFLOW.
            if (opnum != rop.INT_ADD_OVF and
                opnum != rop.INT_SUB_OVF and
                opnum != rop.INT_MUL_OVF):
                return
            # Else, synthesize the non overflowing op for optimize_default to
            # reuse, as well as the reverse op
            elif opnum == rop.INT_ADD_OVF:
                #self.pure(rop.INT_ADD, args[:], result)
                self.pure(rop.INT_SUB, [result, args[1]], args[0])
                self.pure(rop.INT_SUB, [result, args[0]], args[1])
            elif opnum == rop.INT_SUB_OVF:
                #self.pure(rop.INT_SUB, args[:], result)
                self.pure(rop.INT_ADD, [result, args[1]], args[0])
                self.pure(rop.INT_SUB, [args[0], result], args[1])
            #elif opnum == rop.INT_MUL_OVF:
            #    self.pure(rop.INT_MUL, args[:], result)
        self.emit_operation(op)

    def optimize_GUARD_OVERFLOW(self, op):
        # If INT_xxx_OVF was replaced by INT_xxx, *but* we still see
        # GUARD_OVERFLOW, then the loop is invalid.
        lastop = self.last_emitted_operation
        if lastop is None:
            raise InvalidLoop('An INT_xxx_OVF was proven not to overflow but' +
                              'guarded with GUARD_OVERFLOW')
        opnum = lastop.getopnum()
        if opnum not in (rop.INT_ADD_OVF, rop.INT_SUB_OVF, rop.INT_MUL_OVF):
            raise InvalidLoop('An INT_xxx_OVF was proven not to overflow but' +
                              'guarded with GUARD_OVERFLOW')

        self.emit_operation(op)

    def optimize_INT_ADD_OVF(self, op):
        b1 = self.getintbound(op.getarg(0))
        b2 = self.getintbound(op.getarg(1))
        resbound = b1.add_bound(b2)
        if resbound.bounded():
            # Transform into INT_ADD.  The following guard will be killed
            # by optimize_GUARD_NO_OVERFLOW; if we see instead an
            # optimize_GUARD_OVERFLOW, then InvalidLoop.
            op = self.replace_op_with(op, rop.INT_ADD)
        self.emit_operation(op) # emit the op
        r = self.getintbound(op)
        r.intersect(resbound)

    def optimize_INT_SUB_OVF(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        if v1.box is v2.box:
            self.make_constant_int(op, 0)
            return
        resbound = v1.getintbound().sub_bound(v2.getintbound())
        if resbound.bounded():
            op = self.replace_op_with(op, rop.INT_SUB)
        self.emit_operation(op) # emit the op
        r = self.getvalue(op)
        r.getintbound().intersect(resbound)

    def optimize_INT_MUL_OVF(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        resbound = v1.getintbound().mul_bound(v2.getintbound())
        if resbound.bounded():
            op = self.replace_op_with(op, rop.INT_MUL)
        self.emit_operation(op)
        r = self.getvalue(op)
        r.getintbound().intersect(resbound)

    def optimize_INT_LT(self, op):
        arg1 = self.get_box_replacement(op.getarg(0))
        arg2 = self.get_box_replacement(op.getarg(1))
        b1 = self.getintbound(arg1)
        b2 = self.getintbound(arg2)
        if b1.known_lt(b2):
            self.make_constant_int(op, 1)
        elif b1.known_ge(b2) or arg1 is arg2:
            self.make_constant_int(op, 0)
        else:
            self.emit_operation(op)

    def optimize_INT_GT(self, op):
        arg1 = self.get_box_replacement(op.getarg(0))
        arg2 = self.get_box_replacement(op.getarg(1))
        b1 = self.getintbound(arg1)
        b2 = self.getintbound(arg2)
        if b1.known_gt(b2):
            self.make_constant_int(op, 1)
        elif b1.known_le(b2) or arg1 is arg2:
            self.make_constant_int(op, 0)
        else:
            self.emit_operation(op)

    def optimize_INT_LE(self, op):
        arg1 = self.get_box_replacement(op.getarg(0))
        arg2 = self.get_box_replacement(op.getarg(1))
        b1 = self.getintbound(arg1)
        b2 = self.getintbound(arg2)
        if b1.known_le(b2) or arg1 is arg2:
            self.make_constant_int(op, 1)
        elif b1.known_gt(b2):
            self.make_constant_int(op, 0)
        else:
            self.emit_operation(op)

    def optimize_INT_GE(self, op):
        arg1 = self.get_box_replacement(op.getarg(0))
        arg2 = self.get_box_replacement(op.getarg(1))
        b1 = self.getintbound(arg1)
        b2 = self.getintbound(arg2)
        if b1.known_ge(b2) or arg1 is arg2:
            self.make_constant_int(op, 1)
        elif b1.known_lt(b2):
            self.make_constant_int(op, 0)
        else:
            self.emit_operation(op)

    def optimize_INT_EQ(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        if v1.getintbound().known_gt(v2.getintbound()):
            self.make_constant_int(op, 0)
        elif v1.getintbound().known_lt(v2.getintbound()):
            self.make_constant_int(op, 0)
        elif v1.box is v2.box:
            self.make_constant_int(op, 1)
        else:
            self.emit_operation(op)

    def optimize_INT_NE(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        if v1.getintbound().known_gt(v2.getintbound()):
            self.make_constant_int(op, 1)
        elif v1.getintbound().known_lt(v2.getintbound()):
            self.make_constant_int(op, 1)
        elif v1.box is v2.box:
            self.make_constant_int(op, 0)
        else:
            self.emit_operation(op)

    def optimize_INT_FORCE_GE_ZERO(self, op):
        value = self.getvalue(op.getarg(0))
        if value.getintbound().known_ge(IntBound(0, 0)):
            self.make_equal_to(op, value)
        else:
            self.emit_operation(op)

    def optimize_INT_SIGNEXT(self, op):
        b = self.getintbound(op.getarg(0))
        numbits = op.getarg(1).getint() * 8
        start = -(1 << (numbits - 1))
        stop = 1 << (numbits - 1)
        bounds = IntBound(start, stop - 1)
        if bounds.contains_bound(b):
            self.make_equal_to(op, op.getarg(0))
        else:
            self.emit_operation(op)
            bres = self.getintbound(op)
            bres.intersect(bounds)

    def optimize_ARRAYLEN_GC(self, op):
        self.emit_operation(op)
        # XXX
        #array = self.getvalue(op.getarg(0))
        #result = self.getvalue(op)
        #array.make_len_gt(MODE_ARRAY, op.getdescr(), -1)
        #array.getlenbound().bound.intersect(result.getintbound())
        #assert isinstance(result, IntOptValue)
        #result.intbound = array.getlenbound().bound

    def optimize_STRLEN(self, op):
        self.emit_operation(op)
        array = self.getvalue(op.getarg(0))
        result = self.getvalue(op)
        array.make_len_gt(MODE_STR, op.getdescr(), -1)
        array.getlenbound().bound.intersect(result.getintbound())
        assert isinstance(result, IntOptValue)
        result.intbound = array.getlenbound().bound

    def optimize_UNICODELEN(self, op):
        self.emit_operation(op)
        array = self.getvalue(op.getarg(0))
        result = self.getvalue(op)
        array.make_len_gt(MODE_UNICODE, op.getdescr(), -1)
        array.getlenbound().bound.intersect(result.getintbound())
        assert isinstance(result, IntOptValue)        
        result.intbound = array.getlenbound().bound

    def optimize_STRGETITEM(self, op):
        self.emit_operation(op)
        v1 = self.getvalue(op)
        v1.getintbound().make_ge(IntLowerBound(0))
        v1.getintbound().make_lt(IntUpperBound(256))

    def optimize_GETFIELD_RAW_I(self, op):
        self.emit_operation(op)
        descr = op.getdescr()
        if descr.is_integer_bounded():
            v1 = self.getvalue(op)
            v1.getintbound().make_ge(IntLowerBound(descr.get_integer_min()))
            v1.getintbound().make_le(IntUpperBound(descr.get_integer_max()))

    optimize_GETFIELD_RAW_F = optimize_GETFIELD_RAW_I
    optimize_GETFIELD_GC_I = optimize_GETFIELD_RAW_I
    optimize_GETFIELD_GC_R = optimize_GETFIELD_RAW_I
    optimize_GETFIELD_GC_F = optimize_GETFIELD_RAW_I

    optimize_GETINTERIORFIELD_GC_I = optimize_GETFIELD_RAW_I
    optimize_GETINTERIORFIELD_GC_R = optimize_GETFIELD_RAW_I
    optimize_GETINTERIORFIELD_GC_F = optimize_GETFIELD_RAW_I

    def optimize_GETARRAYITEM_RAW_I(self, op):
        self.emit_operation(op)
        descr = op.getdescr()
        if descr and descr.is_item_integer_bounded():
            intbound = self.getvalue(op).getintbound()
            intbound.make_ge(IntLowerBound(descr.get_item_integer_min()))
            intbound.make_le(IntUpperBound(descr.get_item_integer_max()))

    optimize_GETARRAYITEM_RAW_F = optimize_GETARRAYITEM_RAW_I
    optimize_GETARRAYITEM_GC_I = optimize_GETARRAYITEM_RAW_I
    optimize_GETARRAYITEM_GC_F = optimize_GETARRAYITEM_RAW_I
    optimize_GETARRAYITEM_GC_R = optimize_GETARRAYITEM_RAW_I

    def optimize_UNICODEGETITEM(self, op):
        self.emit_operation(op)
        v1 = self.getvalue(op)
        v1.getintbound().make_ge(IntLowerBound(0))

    def make_int_lt(self, box1, box2):
        b1 = self.getintbound(box1)
        b2 = self.getintbound(box2)
        if b1.make_lt(b2):
            self.propagate_bounds_backward(box1)
        if b2.make_gt(b1):
            self.propagate_bounds_backward(box2)

    def make_int_le(self, box1, box2):
        b1 = self.getintbound(box1)
        b2 = self.getintbound(box2)
        if b1.make_le(b2):
            self.propagate_bounds_backward(box1)
        if b2.make_ge(b1):
            self.propagate_bounds_backward(box2)

    def make_int_gt(self, box1, box2):
        self.make_int_lt(box2, box1)

    def make_int_ge(self, box1, box2):
        self.make_int_le(box2, box1)

    def propagate_bounds_INT_LT(self, op):
        r = self.get_box_replacement(op)
        if r.is_constant():
            if r.getint() == 1:
                self.make_int_lt(op.getarg(0), op.getarg(1))
            else:
                assert r.getint() == 0
                self.make_int_ge(op.getarg(0), op.getarg(1))

    def propagate_bounds_INT_GT(self, op):
        r = self.get_box_replacement(op)
        if r.is_constant():
            if r.getint() == 1:
                self.make_int_gt(op.getarg(0), op.getarg(1))
            else:
                assert r.getint() == 0
                self.make_int_le(op.getarg(0), op.getarg(1))

    def propagate_bounds_INT_LE(self, op):
        r = self.get_box_replacement(op)
        if r.is_constant():
            if r.getint() == 1:
                self.make_int_le(op.getarg(0), op.getarg(1))
            else:
                assert r.getint() == 0
                self.make_int_gt(op.getarg(0), op.getarg(1))

    def propagate_bounds_INT_GE(self, op):
        r = self.get_box_replacement(op)
        if r.is_constant():
            if r.getint() == 1:
                self.make_int_ge(op.getarg(0), op.getarg(1))
            else:
                assert r.getint() == 0
                self.make_int_lt(op.getarg(0), op.getarg(1))

    def propagate_bounds_INT_EQ(self, op):
        r = self.getvalue(op)
        if r.is_constant():
            if r.box.same_constant(CONST_1):
                v1 = self.getvalue(op.getarg(0))
                v2 = self.getvalue(op.getarg(1))
                if v1.getintbound().intersect(v2.getintbound()):
                    self.propagate_bounds_backward(op.getarg(0), v1)
                if v2.getintbound().intersect(v1.getintbound()):
                    self.propagate_bounds_backward(op.getarg(1), v2)

    def propagate_bounds_INT_NE(self, op):
        r = self.getvalue(op)
        if r.is_constant():
            if r.box.same_constant(CONST_0):
                v1 = self.getvalue(op.getarg(0))
                v2 = self.getvalue(op.getarg(1))
                if v1.getintbound().intersect(v2.getintbound()):
                    self.propagate_bounds_backward(op.getarg(0), v1)
                if v2.getintbound().intersect(v1.getintbound()):
                    self.propagate_bounds_backward(op.getarg(1), v2)

    def _propagate_int_is_true_or_zero(self, op, valnonzero, valzero):
        r = self.get_box_replacement(op)
        if r.is_constant():
            if r.getint() == valnonzero:
                b1 = self.getintbound(op.getarg(0))
                if b1.known_ge(IntBound(0, 0)):
                    b1.make_gt(IntBound(0, 0))
                    self.propagate_bounds_backward(op.getarg(0))
            elif r.getint() == valzero:
                b1 = self.getintbound(op.getarg(0))
                # XXX remove this hack maybe?
                # Clever hack, we can't use self.make_constant_int yet because
                # the args aren't in the values dictionary yet so it runs into
                # an assert, this is a clever way of expressing the same thing.
                b1.make_ge(IntBound(0, 0))
                b1.make_lt(IntBound(1, 1))
                self.propagate_bounds_backward(op.getarg(0))

    def propagate_bounds_INT_IS_TRUE(self, op):
        self._propagate_int_is_true_or_zero(op, 1, 0)

    def propagate_bounds_INT_IS_ZERO(self, op):
        self._propagate_int_is_true_or_zero(op, 0, 1)

    def propagate_bounds_INT_ADD(self, op):
        b1 = self.getintbound(op.getarg(0))
        b2 = self.getintbound(op.getarg(1))
        r = self.getintbound(op)
        b = r.sub_bound(b2)
        if b1.intersect(b):
            self.propagate_bounds_backward(op.getarg(0))
        b = r.sub_bound(b1)
        if b2.intersect(b):
            self.propagate_bounds_backward(op.getarg(1))

    def propagate_bounds_INT_SUB(self, op):
        b1 = self.getintbound(op.getarg(0))
        b2 = self.getintbound(op.getarg(1))
        r = self.getintbound(op)
        b = r.add_bound(b2)
        if b1.intersect(b):
            self.propagate_bounds_backward(op.getarg(0))
        b = r.sub_bound(b1).mul(-1)
        if b2.intersect(b):
            self.propagate_bounds_backward(op.getarg(1))

    def propagate_bounds_INT_MUL(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        r = self.getvalue(op)
        b = r.getintbound().div_bound(v2.getintbound())
        if v1.getintbound().intersect(b):
            self.propagate_bounds_backward(op.getarg(0), v1)
        b = r.getintbound().div_bound(v1.getintbound())
        if v2.getintbound().intersect(b):
            self.propagate_bounds_backward(op.getarg(1), v2)

    def propagate_bounds_INT_LSHIFT(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        r = self.getvalue(op)
        b = r.getintbound().rshift_bound(v2.getintbound())
        if v1.getintbound().intersect(b):
            self.propagate_bounds_backward(op.getarg(0), v1)

    propagate_bounds_INT_ADD_OVF = propagate_bounds_INT_ADD
    propagate_bounds_INT_SUB_OVF = propagate_bounds_INT_SUB
    propagate_bounds_INT_MUL_OVF = propagate_bounds_INT_MUL


dispatch_opt = make_dispatcher_method(OptIntBounds, 'optimize_',
        default=OptIntBounds.opt_default)
dispatch_bounds_ops = make_dispatcher_method(OptIntBounds, 'propagate_bounds_')

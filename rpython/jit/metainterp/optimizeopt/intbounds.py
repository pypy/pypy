import sys
from rpython.jit.metainterp.history import ConstInt
from rpython.jit.metainterp.optimize import InvalidLoop
from rpython.jit.metainterp.optimizeopt.intutils import IntBound
from rpython.jit.metainterp.optimizeopt.optimizer import (Optimization, CONST_1,
    CONST_0)
from rpython.jit.metainterp.optimizeopt.util import (
    make_dispatcher_method, have_dispatcher_method, get_box_replacement)
from rpython.jit.metainterp.optimizeopt.info import getptrinfo
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.metainterp.optimizeopt import vstring
from rpython.jit.metainterp.optimizeopt import autogenintrules
from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.rlib.rarithmetic import intmask
from rpython.rlib.debug import debug_print
from rpython.rlib import objectmodel

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



class OptIntBounds(Optimization):
    """Keeps track of the bounds placed on integers by guards and remove
       redundant guards"""

    def propagate_forward(self, op):
        return dispatch_opt(self, op)

    def propagate_bounds_backward(self, box):
        # FIXME: This takes care of the instruction where box is the result
        #        but the bounds produced by all instructions where box is
        #        an argument might also be tighten
        b = self.getintbound(box)
        if b.is_constant():
            self.make_constant_int(box, b.get_constant_int())

        box1 = self.optimizer.as_operation(box)
        if box1 is not None:
            dispatch_bounds_ops(self, box1)

    def _postprocess_guard_true_false_value(self, op):
        if op.getarg(0).type == 'i':
            self.propagate_bounds_backward(op.getarg(0))

    postprocess_GUARD_TRUE = _postprocess_guard_true_false_value
    postprocess_GUARD_FALSE = _postprocess_guard_true_false_value
    postprocess_GUARD_VALUE = _postprocess_guard_true_false_value

    def postprocess_INT_OR(self, op):
        arg0 = get_box_replacement(op.getarg(0))
        arg1 = get_box_replacement(op.getarg(1))
        b0 = self.getintbound(arg0)
        b1 = self.getintbound(arg1)
        if b0.and_bound(b1).known_eq_const(0):
            self.pure_from_args(rop.INT_ADD,
                                [arg0, arg1], op)
            self.pure_from_args(rop.INT_XOR,
                                [arg0, arg1], op)
        b = b0.or_bound(b1)
        self.getintbound(op).intersect(b)

    def postprocess_INT_XOR(self, op):
        arg0 = get_box_replacement(op.getarg(0))
        arg1 = get_box_replacement(op.getarg(1))
        b0 = self.getintbound(arg0)
        b1 = self.getintbound(arg1)
        if b0.and_bound(b1).known_eq_const(0):
            self.pure_from_args(rop.INT_ADD,
                                [arg0, arg1], op)
            self.pure_from_args(rop.INT_OR,
                                [arg0, arg1], op)
        b = b0.xor_bound(b1)
        self.getintbound(op).intersect(b)

    def postprocess_INT_AND(self, op):
        b1 = self.getintbound(op.getarg(0))
        b2 = self.getintbound(op.getarg(1))
        b = b1.and_bound(b2)
        self.getintbound(op).intersect(b)

    def postprocess_INT_SUB(self, op):
        import sys
        arg0 = op.getarg(0)
        arg1 = op.getarg(1)
        b0 = self.getintbound(arg0)
        b1 = self.getintbound(arg1)
        b = b0.sub_bound(b1)
        self.getintbound(op).intersect(b)
        self.optimizer.pure_from_args(rop.INT_ADD, [op, arg1], arg0)
        self.optimizer.pure_from_args(rop.INT_SUB, [arg0, op], arg1)
        if isinstance(arg1, ConstInt):
            # invert the constant
            i1 = arg1.getint()
            if i1 == -sys.maxint - 1:
                return
            inv_arg1 = ConstInt(-i1)
            self.optimizer.pure_from_args(rop.INT_ADD, [arg0, inv_arg1], op)
            self.optimizer.pure_from_args(rop.INT_ADD, [inv_arg1, arg0], op)
            self.optimizer.pure_from_args(rop.INT_SUB, [op, inv_arg1], arg0)
            self.optimizer.pure_from_args(rop.INT_SUB, [op, arg0], inv_arg1)


    def postprocess_INT_ADD(self, op):
        import sys
        arg0 = op.getarg(0)
        arg1 = op.getarg(1)
        b0 = self.getintbound(arg0)
        b1 = self.getintbound(arg1)
        b = b0.add_bound(b1)
        self.getintbound(op).intersect(b)
        # Synthesize the reverse op for optimize_default to reuse
        self.optimizer.pure_from_args(rop.INT_SUB, [op, arg1], arg0)
        self.optimizer.pure_from_args(rop.INT_SUB, [op, arg0], arg1)
        if isinstance(arg0, ConstInt):
            # invert the constant
            i0 = arg0.getint()
            if i0 == -sys.maxint - 1:
                return
            inv_arg0 = ConstInt(-i0)
        elif isinstance(arg1, ConstInt):
            # commutative
            i0 = arg1.getint()
            if i0 == -sys.maxint - 1:
                return
            inv_arg0 = ConstInt(-i0)
            arg1 = arg0
        else:
            return
        self.optimizer.pure_from_args(rop.INT_SUB, [arg1, inv_arg0], op)
        self.optimizer.pure_from_args(rop.INT_SUB, [arg1, op], inv_arg0)
        self.optimizer.pure_from_args(rop.INT_ADD, [op, inv_arg0], arg1)
        self.optimizer.pure_from_args(rop.INT_ADD, [inv_arg0, op], arg1)

    def postprocess_INT_MUL(self, op):
        b1 = self.getintbound(op.getarg(0))
        b2 = self.getintbound(op.getarg(1))
        r = self.getintbound(op)
        b = b1.mul_bound(b2)
        r.intersect(b)

    def postprocess_CALL_PURE_I(self, op):
        # dispatch based on 'oopspecindex' to a method that handles
        # specifically the given oopspec call.
        effectinfo = op.getdescr().get_extra_info()
        oopspecindex = effectinfo.oopspecindex
        if oopspecindex == EffectInfo.OS_INT_PY_DIV:
            self.post_call_INT_PY_DIV(op)
        elif oopspecindex == EffectInfo.OS_INT_PY_MOD:
            self.post_call_INT_PY_MOD(op)

    def post_call_INT_PY_DIV(self, op):
        b1 = self.getintbound(op.getarg(1))
        b2 = self.getintbound(op.getarg(2))
        r = self.getintbound(op)
        r.intersect(b1.py_div_bound(b2))

    def post_call_INT_PY_MOD(self, op):
        b1 = self.getintbound(op.getarg(1))
        b2 = self.getintbound(op.getarg(2))
        r = self.getintbound(op)
        r.intersect(b1.mod_bound(b2))

    def postprocess_INT_LSHIFT(self, op):
        arg0 = get_box_replacement(op.getarg(0))
        b1 = self.getintbound(arg0)
        arg1 = get_box_replacement(op.getarg(1))
        b2 = self.getintbound(arg1)
        r = self.getintbound(op)
        b = b1.lshift_bound(b2)
        r.intersect(b)
        if b1.lshift_bound_cannot_overflow(b2):
            # Synthesize the reverse op for optimize_default to reuse.
            # This is important because overflow checking for lshift is done
            # like this (in ll_int_lshift_ovf in rint.py):
            #  result = x << y
            #  if (result >> y) != x:
            #      raise OverflowError("x<<y loosing bits or changing sign")
            self.pure_from_args(rop.INT_RSHIFT,
                                [op, arg1], arg0)

    def postprocess_INT_RSHIFT(self, op):
        b1 = self.getintbound(op.getarg(0))
        b2 = self.getintbound(op.getarg(1))
        b = b1.rshift_bound(b2)
        r = self.getintbound(op)
        r.intersect(b)

    def postprocess_UINT_RSHIFT(self, op):
        b1 = self.getintbound(op.getarg(0))
        b2 = self.getintbound(op.getarg(1))
        b = b1.urshift_bound(b2)
        r = self.getintbound(op)
        r.intersect(b)

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
                self.pure_from_args(rop.INT_SUB, [result, args[1]], args[0])
                self.pure_from_args(rop.INT_SUB, [result, args[0]], args[1])
            elif opnum == rop.INT_SUB_OVF:
                #self.pure(rop.INT_SUB, args[:], result)
                self.pure_from_args(rop.INT_ADD, [result, args[1]], args[0])
                self.pure_from_args(rop.INT_SUB, [args[0], result], args[1])
            #elif opnum == rop.INT_MUL_OVF:
            #    self.pure(rop.INT_MUL, args[:], result)
            return self.emit(op)

    def optimize_GUARD_OVERFLOW(self, op):
        # If INT_xxx_OVF was replaced by INT_xxx, *but* we still see
        # GUARD_OVERFLOW, then the loop is invalid.
        lastop = self.last_emitted_operation
        if lastop is None:
            return # e.g. beginning of the loop
        opnum = lastop.getopnum()
        if opnum not in (rop.INT_ADD_OVF, rop.INT_SUB_OVF, rop.INT_MUL_OVF):
            raise InvalidLoop('An INT_xxx_OVF was proven not to overflow but' +
                              'guarded with GUARD_OVERFLOW')

        return self.emit(op)

    def optimize_INT_ADD_OVF(self, op):
        b1 = self.getintbound(op.getarg(0))
        b2 = self.getintbound(op.getarg(1))
        if b1.add_bound_cannot_overflow(b2):
            # Transform into INT_ADD.  The following guard will be killed
            # by optimize_GUARD_NO_OVERFLOW; if we see instead an
            # optimize_GUARD_OVERFLOW, then InvalidLoop.

            # NB: this case also takes care of int_add_ovf with 0 as one of the
            # arguments
            op = self.replace_op_with(op, rop.INT_ADD)
            return self.optimizer.send_extra_operation(op)
        return self.emit(op)

    def postprocess_INT_ADD_OVF(self, op):
        b1 = self.getintbound(op.getarg(0))
        b2 = self.getintbound(op.getarg(1))
        # we can always give the result a bound. if the int_add_ovf is followed
        # by a guard_no_overflow, then we know no overflow occurred, and the
        # bound is correct. Otherwise, it must be followed by a guard_overflow
        # and it is also fine to give the result a bound, because the result
        # box must never be used in the rest of the trace
        resbound = b1.add_bound_no_overflow(b2)
        r = self.getintbound(op)
        r.intersect(resbound)

    def optimize_INT_SUB_OVF(self, op):
        arg0 = get_box_replacement(op.getarg(0))
        arg1 = get_box_replacement(op.getarg(1))
        b0 = self.getintbound(arg0)
        b1 = self.getintbound(arg1)
        if arg0.same_box(arg1):
            self.make_constant_int(op, 0)
            return None
        if b0.sub_bound_cannot_overflow(b1):
            # this case takes care of int_sub_ovf(x, 0) as well
            op = self.replace_op_with(op, rop.INT_SUB)
            return self.optimizer.send_extra_operation(op)
        return self.emit(op)

    def postprocess_INT_SUB_OVF(self, op):
        arg0 = get_box_replacement(op.getarg(0))
        arg1 = get_box_replacement(op.getarg(1))
        b0 = self.getintbound(arg0)
        b1 = self.getintbound(arg1)
        resbound = b0.sub_bound_no_overflow(b1)
        r = self.getintbound(op)
        r.intersect(resbound)

    def optimize_INT_MUL_OVF(self, op):
        b0 = self.getintbound(op.getarg(0))
        b1 = self.getintbound(op.getarg(1))
        if b0.mul_bound_cannot_overflow(b1):
            # this case also takes care of multiplication with 0 and 1
            op = self.replace_op_with(op, rop.INT_MUL)
            return self.optimizer.send_extra_operation(op)
        return self.emit(op)

    def postprocess_INT_MUL_OVF(self, op):
        b1 = self.getintbound(op.getarg(0))
        b2 = self.getintbound(op.getarg(1))
        resbound = b1.mul_bound_no_overflow(b2)
        r = self.getintbound(op)
        r.intersect(resbound)

    def optimize_INT_LT(self, op):
        arg1 = get_box_replacement(op.getarg(0))
        arg2 = get_box_replacement(op.getarg(1))
        b1 = self.getintbound(arg1)
        b2 = self.getintbound(arg2)
        if b1.known_lt(b2):
            self.make_constant_int(op, 1)
        elif b1.known_ge(b2) or arg1 is arg2:
            self.make_constant_int(op, 0)
        else:
            return self.emit(op)

    def optimize_INT_GT(self, op):
        arg1 = get_box_replacement(op.getarg(0))
        arg2 = get_box_replacement(op.getarg(1))
        b1 = self.getintbound(arg1)
        b2 = self.getintbound(arg2)
        if b1.known_gt(b2):
            self.make_constant_int(op, 1)
        elif b1.known_le(b2) or arg1 is arg2:
            self.make_constant_int(op, 0)
        else:
            return self.emit(op)

    def optimize_INT_LE(self, op):
        arg1 = get_box_replacement(op.getarg(0))
        arg2 = get_box_replacement(op.getarg(1))
        b1 = self.getintbound(arg1)
        b2 = self.getintbound(arg2)
        if b1.known_le(b2) or arg1 is arg2:
            self.make_constant_int(op, 1)
        elif b1.known_gt(b2):
            self.make_constant_int(op, 0)
        else:
            return self.emit(op)

    def optimize_INT_GE(self, op):
        arg1 = get_box_replacement(op.getarg(0))
        arg2 = get_box_replacement(op.getarg(1))
        b1 = self.getintbound(arg1)
        b2 = self.getintbound(arg2)
        if b1.known_ge(b2) or arg1 is arg2:
            self.make_constant_int(op, 1)
        elif b1.known_lt(b2):
            self.make_constant_int(op, 0)
        else:
            return self.emit(op)

    def optimize_UINT_LT(self, op):
        arg1 = get_box_replacement(op.getarg(0))
        arg2 = get_box_replacement(op.getarg(1))
        b1 = self.getintbound(arg1)
        b2 = self.getintbound(arg2)
        if b1.known_unsigned_lt(b2):
            self.make_constant_int(op, 1)
        elif b1.known_unsigned_ge(b2) or arg1 is arg2:
            self.make_constant_int(op, 0)
        else:
            return self.emit(op)

    def propagate_bounds_UINT_LT(self, op):
        r = self.getintbound(op)
        if r.is_constant():
            if r.get_constant_int() == 1:
                self.make_unsigned_lt(op.getarg(0), op.getarg(1))
            else:
                assert r.get_constant_int() == 0
                self.make_unsigned_ge(op.getarg(0), op.getarg(1))

    def optimize_UINT_GT(self, op):
        arg1 = get_box_replacement(op.getarg(0))
        arg2 = get_box_replacement(op.getarg(1))
        b1 = self.getintbound(arg1)
        b2 = self.getintbound(arg2)
        if b1.known_unsigned_gt(b2):
            self.make_constant_int(op, 1)
        elif b1.known_unsigned_le(b2) or arg1 is arg2:
            self.make_constant_int(op, 0)
        else:
            return self.emit(op)

    def propagate_bounds_UINT_GT(self, op):
        r = self.getintbound(op)
        if r.is_constant():
            if r.get_constant_int() == 1:
                self.make_unsigned_gt(op.getarg(0), op.getarg(1))
            else:
                assert r.get_constant_int() == 0
                self.make_unsigned_le(op.getarg(0), op.getarg(1))

    def optimize_UINT_LE(self, op):
        arg1 = get_box_replacement(op.getarg(0))
        arg2 = get_box_replacement(op.getarg(1))
        b1 = self.getintbound(arg1)
        b2 = self.getintbound(arg2)
        if b1.known_unsigned_le(b2) or arg1 is arg2:
            self.make_constant_int(op, 1)
        elif b1.known_unsigned_gt(b2):
            self.make_constant_int(op, 0)
        else:
            return self.emit(op)

    def propagate_bounds_UINT_LE(self, op):
        r = self.getintbound(op)
        if r.is_constant():
            if r.get_constant_int() == 1:
                self.make_unsigned_le(op.getarg(0), op.getarg(1))
            else:
                assert r.get_constant_int() == 0
                self.make_unsigned_gt(op.getarg(0), op.getarg(1))

    def optimize_UINT_GE(self, op):
        arg1 = get_box_replacement(op.getarg(0))
        arg2 = get_box_replacement(op.getarg(1))
        b1 = self.getintbound(arg1)
        b2 = self.getintbound(arg2)
        if b1.known_unsigned_ge(b2) or arg1 is arg2:
            self.make_constant_int(op, 1)
        elif b1.known_unsigned_lt(b2):
            self.make_constant_int(op, 0)
        else:
            return self.emit(op)

    def propagate_bounds_UINT_GE(self, op):
        r = self.getintbound(op)
        if r.is_constant():
            if r.get_constant_int() == 1:
                self.make_unsigned_ge(op.getarg(0), op.getarg(1))
            else:
                assert r.get_constant_int() == 0
                self.make_unsigned_lt(op.getarg(0), op.getarg(1))

    def optimize_INT_SIGNEXT(self, op):
        b = self.getintbound(op.getarg(0))
        numbits = op.getarg(1).getint() * 8
        start = -(1 << (numbits - 1))
        stop = 1 << (numbits - 1)
        if b.is_within_range(start, stop - 1):
            self.make_equal_to(op, op.getarg(0))
        else:
            return self.emit(op)

    def postprocess_INT_SIGNEXT(self, op):
        numbits = op.getarg(1).getint() * 8
        start = -(1 << (numbits - 1))
        stop = 1 << (numbits - 1)
        bres = self.getintbound(op)
        bres.intersect_const(start, stop - 1)

    def postprocess_INT_FORCE_GE_ZERO(self, op):
        b = self.getintbound(op)
        b.make_ge_const(0)
        b1 = self.getintbound(op.getarg(0))
        if b1.upper >= 0:
            b.make_le(b1)

    def postprocess_INT_INVERT(self, op):
        b = self.getintbound(op.getarg(0))
        bounds = b.invert_bound()
        bres = self.getintbound(op)
        bres.intersect(bounds)

    def propagate_bounds_INT_INVERT(self, op):
        arg0 = get_box_replacement(op.getarg(0))
        b = self.getintbound(arg0)
        bres = self.getintbound(op)
        bounds = bres.invert_bound()
        if b.intersect(bounds):
            self.propagate_bounds_backward(arg0)

    def propagate_bounds_INT_NEG(self, op):
        arg0 = get_box_replacement(op.getarg(0))
        b = self.getintbound(arg0)
        bres = self.getintbound(op)
        bounds = bres.neg_bound()
        if b.intersect(bounds):
            self.propagate_bounds_backward(arg0)

    def postprocess_INT_NEG(self, op):
        b = self.getintbound(op.getarg(0))
        bounds = b.neg_bound()
        bres = self.getintbound(op)
        bres.intersect(bounds)

    def postprocess_ARRAYLEN_GC(self, op):
        array = self.ensure_ptr_info_arg0(op)
        self.optimizer.setintbound(op, array.getlenbound(None))

    def postprocess_STRLEN(self, op):
        self.make_nonnull_str(op.getarg(0), vstring.mode_string)
        array = getptrinfo(op.getarg(0))
        self.optimizer.setintbound(op, array.getlenbound(vstring.mode_string))

    def postprocess_UNICODELEN(self, op):
        self.make_nonnull_str(op.getarg(0), vstring.mode_unicode)
        array = getptrinfo(op.getarg(0))
        self.optimizer.setintbound(op, array.getlenbound(vstring.mode_unicode))

    def postprocess_STRGETITEM(self, op):
        v1 = self.getintbound(op)
        v2 = getptrinfo(op.getarg(0))
        intbound = self.getintbound(op.getarg(1))
        if v2 is not None:
            lenbound = v2.getlenbound(vstring.mode_string)
            if lenbound is not None:
                lenbound.make_gt_const(intbound.lower)
        v1.intersect_const(0, 255)

    def postprocess_GETFIELD_RAW_I(self, op):
        descr = op.getdescr()
        if descr.is_integer_bounded():
            b1 = self.getintbound(op)
            b1.intersect_const(descr.get_integer_min(), descr.get_integer_max())

    postprocess_GETFIELD_RAW_F = postprocess_GETFIELD_RAW_I
    postprocess_GETFIELD_RAW_R = postprocess_GETFIELD_RAW_I
    postprocess_GETFIELD_GC_I = postprocess_GETFIELD_RAW_I
    postprocess_GETFIELD_GC_R = postprocess_GETFIELD_RAW_I
    postprocess_GETFIELD_GC_F = postprocess_GETFIELD_RAW_I

    postprocess_GETINTERIORFIELD_GC_I = postprocess_GETFIELD_RAW_I
    postprocess_GETINTERIORFIELD_GC_R = postprocess_GETFIELD_RAW_I
    postprocess_GETINTERIORFIELD_GC_F = postprocess_GETFIELD_RAW_I

    def postprocess_GETARRAYITEM_RAW_I(self, op):
        descr = op.getdescr()
        if descr and descr.is_item_integer_bounded():
            intbound = self.getintbound(op)
            intbound.intersect_const(descr.get_item_integer_min(), descr.get_item_integer_max())

    postprocess_GETARRAYITEM_RAW_F = postprocess_GETARRAYITEM_RAW_I
    postprocess_GETARRAYITEM_GC_I = postprocess_GETARRAYITEM_RAW_I
    postprocess_GETARRAYITEM_GC_F = postprocess_GETARRAYITEM_RAW_I
    postprocess_GETARRAYITEM_GC_R = postprocess_GETARRAYITEM_RAW_I

    def postprocess_UNICODEGETITEM(self, op):
        b1 = self.getintbound(op)
        b1.make_ge_const(0)
        v2 = getptrinfo(op.getarg(0))
        intbound = self.getintbound(op.getarg(1))
        if v2 is not None:
            lenbound = v2.getlenbound(vstring.mode_unicode)
            if lenbound is not None:
                lenbound.make_gt_const(intbound.lower)

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

    def make_unsigned_lt(self, box1, box2):
        b1 = self.getintbound(box1)
        b2 = self.getintbound(box2)
        if b1.make_unsigned_lt(b2):
            self.propagate_bounds_backward(box1)
        if b2.make_unsigned_gt(b1):
            self.propagate_bounds_backward(box2)

    def make_unsigned_le(self, box1, box2):
        b1 = self.getintbound(box1)
        b2 = self.getintbound(box2)
        if b1.make_unsigned_le(b2):
            self.propagate_bounds_backward(box1)
        if b2.make_unsigned_ge(b1):
            self.propagate_bounds_backward(box2)

    def make_unsigned_gt(self, box1, box2):
        self.make_unsigned_lt(box2, box1)

    def make_unsigned_ge(self, box1, box2):
        self.make_unsigned_le(box2, box1)

    def propagate_bounds_INT_LT(self, op):
        r = self.getintbound(op)
        if r.is_constant():
            if r.get_constant_int() == 1:
                self.make_int_lt(op.getarg(0), op.getarg(1))
            else:
                assert r.get_constant_int() == 0
                self.make_int_ge(op.getarg(0), op.getarg(1))

    def propagate_bounds_INT_GT(self, op):
        r = self.getintbound(op)
        if r.is_constant():
            if r.get_constant_int() == 1:
                self.make_int_gt(op.getarg(0), op.getarg(1))
            else:
                assert r.get_constant_int() == 0
                self.make_int_le(op.getarg(0), op.getarg(1))

    def propagate_bounds_INT_LE(self, op):
        r = self.getintbound(op)
        if r.is_constant():
            if r.get_constant_int() == 1:
                self.make_int_le(op.getarg(0), op.getarg(1))
            else:
                assert r.get_constant_int() == 0
                self.make_int_gt(op.getarg(0), op.getarg(1))

    def propagate_bounds_INT_GE(self, op):
        r = self.getintbound(op)
        if r.is_constant():
            if r.get_constant_int() == 1:
                self.make_int_ge(op.getarg(0), op.getarg(1))
            else:
                assert r.get_constant_int() == 0
                self.make_int_lt(op.getarg(0), op.getarg(1))

    def propagate_bounds_INT_EQ(self, op):
        r = self.getintbound(op)
        if r.known_eq_const(1):
            self.make_eq(op.getarg(0), op.getarg(1))
        elif r.known_eq_const(0):
            self.make_ne(op.getarg(0), op.getarg(1))

    def propagate_bounds_INT_NE(self, op):
        r = self.getintbound(op)
        if r.known_eq_const(0):
            self.make_eq(op.getarg(0), op.getarg(1))
        elif r.known_eq_const(1):
            self.make_ne(op.getarg(0), op.getarg(1))

    def make_eq(self, arg0, arg1):
        b0 = self.getintbound(arg0)
        b1 = self.getintbound(arg1)
        if b0.intersect(b1):
            self.propagate_bounds_backward(arg0)
        if b1.intersect(b0):
            self.propagate_bounds_backward(arg1)

    def make_ne(self, arg0, arg1):
        b0 = self.getintbound(arg0)
        b1 = self.getintbound(arg1)
        if b1.is_constant():
            v1 = b1.get_constant_int()
            if b0.make_ne_const(v1):
                self.propagate_bounds_backward(arg0)
        elif b0.is_constant():
            v0 = b0.get_constant_int()
            if b1.make_ne_const(v0):
                self.propagate_bounds_backward(arg1)

    def _propagate_int_is_true_or_zero(self, op, valnonzero, valzero):
        if self.is_raw_ptr(op.getarg(0)):
            return
        r = self.getintbound(op)
        if r.is_constant():
            if r.get_constant_int() == valnonzero:
                b1 = self.getintbound(op.getarg(0))
                if b1.known_nonnegative():
                    b1.make_gt_const(0)
                    self.propagate_bounds_backward(op.getarg(0))
                elif b1.known_le_const(0):
                    b1.make_lt_const(0)
                    self.propagate_bounds_backward(op.getarg(0))
            elif r.get_constant_int() == valzero:
                self.make_constant_int(op.getarg(0), 0)
                self.propagate_bounds_backward(op.getarg(0))

    def propagate_bounds_INT_IS_TRUE(self, op):
        self._propagate_int_is_true_or_zero(op, 1, 0)

    def propagate_bounds_INT_IS_ZERO(self, op):
        self._propagate_int_is_true_or_zero(op, 0, 1)

    def propagate_bounds_INT_ADD(self, op):
        if self.is_raw_ptr(op.getarg(0)) or self.is_raw_ptr(op.getarg(1)):
            return
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
        b = r.sub_bound(b1).neg_bound()
        if b2.intersect(b):
            self.propagate_bounds_backward(op.getarg(1))

    def propagate_bounds_INT_MUL(self, op):
        b1 = self.getintbound(op.getarg(0))
        b2 = self.getintbound(op.getarg(1))
        if op.opnum != rop.INT_MUL_OVF and not b1.mul_bound_cannot_overflow(b2):
            # we can only do divide if the operation didn't overflow
            return
        r = self.getintbound(op)
        b = r.py_div_bound(b2)
        if b1.intersect(b):
            self.propagate_bounds_backward(op.getarg(0))
        b = r.py_div_bound(b1)
        if b2.intersect(b):
            self.propagate_bounds_backward(op.getarg(1))

    def propagate_bounds_INT_LSHIFT(self, op):
        b1 = self.getintbound(op.getarg(0))
        b2 = self.getintbound(op.getarg(1))
        if not b1.lshift_bound_cannot_overflow(b2):
            return
        r = self.getintbound(op)
        b = r.lshift_bound_backwards(b2)
        if b1.intersect(b):
            self.propagate_bounds_backward(op.getarg(0))

    def propagate_bounds_UINT_RSHIFT(self, op):
        b1 = self.getintbound(op.getarg(0))
        b2 = self.getintbound(op.getarg(1))
        if not b2.is_constant():
            return
        r = self.getintbound(op)
        b = r.urshift_bound_backwards(b2)
        if b1.intersect(b):
            self.propagate_bounds_backward(op.getarg(0))

    def propagate_bounds_INT_RSHIFT(self, op):
        b1 = self.getintbound(op.getarg(0))
        b2 = self.getintbound(op.getarg(1))
        if not b2.is_constant():
            return
        r = self.getintbound(op)
        b = r.rshift_bound_backwards(b2)
        if b1.intersect(b):
            self.propagate_bounds_backward(op.getarg(0))

    propagate_bounds_INT_ADD_OVF = propagate_bounds_INT_ADD
    propagate_bounds_INT_SUB_OVF = propagate_bounds_INT_SUB
    propagate_bounds_INT_MUL_OVF = propagate_bounds_INT_MUL

    def propagate_bounds_INT_AND(self, op):
        r = self.getintbound(op)
        b0 = self.getintbound(op.getarg(0))
        b1 = self.getintbound(op.getarg(1))
        b = b0.and_bound_backwards(r)
        if b1.intersect(b):
            self.propagate_bounds_backward(op.getarg(1))
        b = b1.and_bound_backwards(r)
        if b0.intersect(b):
            self.propagate_bounds_backward(op.getarg(0))

    def propagate_bounds_INT_OR(self, op):
        r = self.getintbound(op)
        b0 = self.getintbound(op.getarg(0))
        b1 = self.getintbound(op.getarg(1))
        b = b0.or_bound_backwards(r)
        if b1.intersect(b):
            self.propagate_bounds_backward(op.getarg(1))
        b = b1.or_bound_backwards(r)
        if b0.intersect(b):
            self.propagate_bounds_backward(op.getarg(0))

    def propagate_bounds_INT_XOR(self, op):
        r = self.getintbound(op)
        b0 = self.getintbound(op.getarg(0))
        b1 = self.getintbound(op.getarg(1))
        b = b0.xor_bound(r) # xor is its own inverse
        if b1.intersect(b):
            self.propagate_bounds_backward(op.getarg(1))
        b = b1.xor_bound(r)
        if b0.intersect(b):
            self.propagate_bounds_backward(op.getarg(0))

    objectmodel.import_from_mixin(autogenintrules.OptIntAutoGenerated)

dispatch_opt = make_dispatcher_method(OptIntBounds, 'optimize_',
                                      default=OptIntBounds.emit)
dispatch_bounds_ops = make_dispatcher_method(OptIntBounds, 'propagate_bounds_')
OptIntBounds.propagate_postprocess = make_dispatcher_method(OptIntBounds, 'postprocess_')
OptIntBounds.have_postprocess_op = have_dispatcher_method(OptIntBounds, 'postprocess_')


class IntegerAnalysisLogger(object):
    def __init__(self, optimizer):
        from rpython.jit.metainterp.logger import LogOperations

        self.optimizer = optimizer
        self.log_operations = LogOperations(
                    optimizer.metainterp_sd, False, None)
        self.last_printed_repr_memo = {}

    def log_op(self, op):
        # print the intbound of all arguments (they might have changed since
        # they were produced)
        for i in range(op.numargs()):
            arg = get_box_replacement(op.getarg(i))
            if arg.type != 'i' or arg.is_constant():
                continue
            b = arg.get_forwarded()
            if not isinstance(b, IntBound) or b.is_unbounded():
                continue
            argop = self.optimizer.as_operation(arg)
            if argop is not None and rop.returns_bool_result(arg.opnum) and b.is_bool():
                continue
            r = b.__repr__()
            if self.last_printed_repr_memo.get(arg, '') == r:
                continue
            self.last_printed_repr_memo[arg] = r
            debug_print("# %s: %s   %s" % (
                self.log_operations.repr_of_arg(arg), b.__str__(), r))
        debug_print(self.log_operations.repr_of_resop(op))

    def log_result(self, op):
        if op.type == 'i':
            b = op.get_forwarded()
            if not isinstance(b, IntBound):
                return
            if rop.returns_bool_result(op.opnum):
                return
            # print the result bound too
            r = b.__repr__()
            debug_print("# %s -> %s   %s" % (
                self.log_operations.repr_of_arg(op), b.__str__(), r))
            self.last_printed_repr_memo[op] = r

    def log_inputargs(self, inputargs):
        args = ", ".join([self.log_operations.repr_of_arg(arg) for arg in inputargs])
        debug_print('[' + args + ']')

def print_rewrite_rule_statistics():
    from rpython.rlib.debug import debug_start, debug_stop, have_debug_prints
    debug_start("jit-intbounds-stats")
    if have_debug_prints():
        for opname, names, counts in OptIntBounds._all_rules_fired:
            debug_print(opname)
            for index in range(len(names)):
                debug_print("    " + names[index], counts[index])
    debug_stop("jit-intbounds-stats")

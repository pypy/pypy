from pypy.jit.metainterp.optimizeopt.optimizer import Optimization, CONST_1, CONST_0
from pypy.jit.metainterp.optimizeopt.util import _findall
from pypy.jit.metainterp.optimizeopt.intutils import (IntBound, IntUnbounded,
    IntLowerBound, IntUpperBound)
from pypy.jit.metainterp.history import Const, ConstInt
from pypy.jit.metainterp.resoperation import rop, ResOperation

class OptIntBounds(Optimization):
    """Keeps track of the bounds placed on integers by guards and remove
       redundant guards"""

    def setup(self):
        self.posponedop = None
        self.nextop = None

    def new(self):
        assert self.posponedop is None
        return OptIntBounds()
        
    def reconstruct_for_next_iteration(self,  short_boxes, surviving_boxes, optimizer,
                                       valuemap):
        assert self.posponedop is None
        return OptIntBounds()

    def flush(self):
        assert self.posponedop is None

    def setup(self):
        self.posponedop = None
        self.nextop = None

    def propagate_forward(self, op):
        if op.is_ovf():
            self.posponedop = op
            return
        if self.posponedop:
            self.nextop = op
            op = self.posponedop
            self.posponedop = None

        opnum = op.getopnum()
        for value, func in optimize_ops:
            if opnum == value:
                func(self, op)
                break
        else:
            assert not op.is_ovf()
            self.emit_operation(op)


    def propagate_bounds_backward(self, box):
        # FIXME: This takes care of the instruction where box is the reuslt
        #        but the bounds produced by all instructions where box is
        #        an argument might also be tighten
        v = self.getvalue(box)
        b = v.intbound
        if b.has_lower and b.has_upper and b.lower == b.upper:
            v.make_constant(ConstInt(b.lower))

        try:
            op = self.optimizer.producer[box]
        except KeyError:
            return
        opnum = op.getopnum()
        for value, func in propagate_bounds_ops:
            if opnum == value:
                func(self, op)
                break

    def optimize_GUARD_TRUE(self, op):
        self.emit_operation(op)
        self.propagate_bounds_backward(op.getarg(0))

    optimize_GUARD_FALSE = optimize_GUARD_TRUE
    optimize_GUARD_VALUE = optimize_GUARD_TRUE

    def optimize_INT_XOR(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        if v1 is v2:
            self.make_constant_int(op.result, 0)
            return
        self.emit_operation(op)
        if v1.intbound.known_ge(IntBound(0, 0)) and \
           v2.intbound.known_ge(IntBound(0, 0)):
            r = self.getvalue(op.result)
            r.intbound.make_ge(IntLowerBound(0))

    def optimize_INT_AND(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        self.emit_operation(op)

        r = self.getvalue(op.result)
        if v2.is_constant():
            val = v2.box.getint()
            if val >= 0:
                r.intbound.intersect(IntBound(0,val))
        elif v1.is_constant():
            val = v1.box.getint()
            if val >= 0:
                r.intbound.intersect(IntBound(0,val))

    def optimize_INT_SUB(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        self.emit_operation(op)
        r = self.getvalue(op.result)
        b = v1.intbound.sub_bound(v2.intbound)
        if b.bounded():
            r.intbound.intersect(b)

    def optimize_INT_ADD(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        self.emit_operation(op)
        r = self.getvalue(op.result)
        b = v1.intbound.add_bound(v2.intbound)
        if b.bounded():
            r.intbound.intersect(b)

    def optimize_INT_MUL(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        self.emit_operation(op)
        r = self.getvalue(op.result)
        b = v1.intbound.mul_bound(v2.intbound)
        if b.bounded():
            r.intbound.intersect(b)

    def optimize_INT_FLOORDIV(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        self.emit_operation(op)
        r = self.getvalue(op.result)
        r.intbound.intersect(v1.intbound.div_bound(v2.intbound))

    def optimize_INT_LSHIFT(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        self.emit_operation(op)
        r = self.getvalue(op.result)
        b = v1.intbound.lshift_bound(v2.intbound)
        r.intbound.intersect(b)
        # intbound.lshift_bound checks for an overflow and if the
        # lshift can be proven not to overflow sets b.has_upper and
        # b.has_lower
        if b.has_lower and b.has_upper:
            # Synthesize the reverse op for optimize_default to reuse
            self.pure(rop.INT_RSHIFT, [op.result, op.getarg(1)], op.getarg(0))

    def optimize_INT_RSHIFT(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        self.emit_operation(op)
        r = self.getvalue(op.result)
        r.intbound.intersect(v1.intbound.rshift_bound(v2.intbound))

    def optimize_INT_ADD_OVF(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        resbound = v1.intbound.add_bound(v2.intbound)
        if resbound.has_lower and resbound.has_upper and \
           self.nextop.getopnum() == rop.GUARD_NO_OVERFLOW:
            # Transform into INT_ADD and remove guard
            op = op.copy_and_change(rop.INT_ADD)
            self.optimize_INT_ADD(op) # emit the op
        else:
            self.emit_operation(op)
            r = self.getvalue(op.result)
            r.intbound.intersect(resbound)
            self.emit_operation(self.nextop)
            if self.nextop.getopnum() == rop.GUARD_NO_OVERFLOW:
                # Synthesize the non overflowing op for optimize_default to reuse
                self.pure(rop.INT_ADD, op.getarglist()[:], op.result)
                # Synthesize the reverse op for optimize_default to reuse
                self.pure(rop.INT_SUB, [op.result, op.getarg(1)], op.getarg(0))
                self.pure(rop.INT_SUB, [op.result, op.getarg(0)], op.getarg(1))


    def optimize_INT_SUB_OVF(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        resbound = v1.intbound.sub_bound(v2.intbound)
        if resbound.has_lower and resbound.has_upper and \
               self.nextop.getopnum() == rop.GUARD_NO_OVERFLOW:
            # Transform into INT_SUB and remove guard
            op = op.copy_and_change(rop.INT_SUB)
            self.optimize_INT_SUB(op) # emit the op
        else:
            self.emit_operation(op)
            r = self.getvalue(op.result)
            r.intbound.intersect(resbound)
            self.emit_operation(self.nextop)
            if self.nextop.getopnum() == rop.GUARD_NO_OVERFLOW:
                # Synthesize the non overflowing op for optimize_default to reuse
                self.pure(rop.INT_SUB, op.getarglist()[:], op.result)
                # Synthesize the reverse ops for optimize_default to reuse
                self.pure(rop.INT_ADD, [op.result, op.getarg(1)], op.getarg(0))
                self.pure(rop.INT_SUB, [op.getarg(0), op.result], op.getarg(1))


    def optimize_INT_MUL_OVF(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        resbound = v1.intbound.mul_bound(v2.intbound)
        if resbound.has_lower and resbound.has_upper and \
               self.nextop.getopnum() == rop.GUARD_NO_OVERFLOW:
            # Transform into INT_MUL and remove guard
            op = op.copy_and_change(rop.INT_MUL)
            self.optimize_INT_MUL(op) # emit the op
        else:
            self.emit_operation(op)
            r = self.getvalue(op.result)
            r.intbound.intersect(resbound)
            self.emit_operation(self.nextop)
            if self.nextop.getopnum() == rop.GUARD_NO_OVERFLOW:
                # Synthesize the non overflowing op for optimize_default to reuse
                self.pure(rop.INT_MUL, op.getarglist()[:], op.result)


    def optimize_INT_LT(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        if v1.intbound.known_lt(v2.intbound):
            self.make_constant_int(op.result, 1)
        elif v1.intbound.known_ge(v2.intbound) or v1 is v2:
            self.make_constant_int(op.result, 0)
        else:
            self.emit_operation(op)

    def optimize_INT_GT(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        if v1.intbound.known_gt(v2.intbound):
            self.make_constant_int(op.result, 1)
        elif v1.intbound.known_le(v2.intbound) or v1 is v2:
            self.make_constant_int(op.result, 0)
        else:
            self.emit_operation(op)

    def optimize_INT_LE(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        if v1.intbound.known_le(v2.intbound) or v1 is v2:
            self.make_constant_int(op.result, 1)
        elif v1.intbound.known_gt(v2.intbound):
            self.make_constant_int(op.result, 0)
        else:
            self.emit_operation(op)

    def optimize_INT_GE(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        if v1.intbound.known_ge(v2.intbound) or v1 is v2:
            self.make_constant_int(op.result, 1)
        elif v1.intbound.known_lt(v2.intbound):
            self.make_constant_int(op.result, 0)
        else:
            self.emit_operation(op)

    def optimize_INT_EQ(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        if v1.intbound.known_gt(v2.intbound):
            self.make_constant_int(op.result, 0)
        elif v1.intbound.known_lt(v2.intbound):
            self.make_constant_int(op.result, 0)
        elif v1 is v2:
            self.make_constant_int(op.result, 1)
        else:
            self.emit_operation(op)

    def optimize_INT_NE(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        if v1.intbound.known_gt(v2.intbound):
            self.make_constant_int(op.result, 1)
        elif v1.intbound.known_lt(v2.intbound):
            self.make_constant_int(op.result, 1)
        elif v1 is v2:
            self.make_constant_int(op.result, 0)
        else:
            self.emit_operation(op)

    def optimize_ARRAYLEN_GC(self, op):
        self.emit_operation(op)
        v1 = self.getvalue(op.result)
        v1.intbound.make_ge(IntLowerBound(0))

    optimize_STRLEN = optimize_UNICODELEN = optimize_ARRAYLEN_GC

    def optimize_STRGETITEM(self, op):
        self.emit_operation(op)
        v1 = self.getvalue(op.result)
        v1.intbound.make_ge(IntLowerBound(0))
        v1.intbound.make_lt(IntUpperBound(256))

    def optimize_UNICODEGETITEM(self, op):
        self.emit_operation(op)
        v1 = self.getvalue(op.result)
        v1.intbound.make_ge(IntLowerBound(0))

    def make_int_lt(self, box1, box2):
        v1 = self.getvalue(box1)
        v2 = self.getvalue(box2)
        if v1.intbound.make_lt(v2.intbound):
            self.propagate_bounds_backward(box1)
        if v2.intbound.make_gt(v1.intbound):
            self.propagate_bounds_backward(box2)

    def make_int_le(self, box1, box2):
        v1 = self.getvalue(box1)
        v2 = self.getvalue(box2)
        if v1.intbound.make_le(v2.intbound):
            self.propagate_bounds_backward(box1)
        if v2.intbound.make_ge(v1.intbound):
            self.propagate_bounds_backward(box2)

    def make_int_gt(self, box1, box2):
        self.make_int_lt(box2, box1)

    def make_int_ge(self, box1, box2):
        self.make_int_le(box2, box1)

    def propagate_bounds_INT_LT(self, op):
        r = self.getvalue(op.result)
        if r.is_constant():
            if r.box.same_constant(CONST_1):
                self.make_int_lt(op.getarg(0), op.getarg(1))
            else:
                self.make_int_ge(op.getarg(0), op.getarg(1))

    def propagate_bounds_INT_GT(self, op):
        r = self.getvalue(op.result)
        if r.is_constant():
            if r.box.same_constant(CONST_1):
                self.make_int_gt(op.getarg(0), op.getarg(1))
            else:
                self.make_int_le(op.getarg(0), op.getarg(1))

    def propagate_bounds_INT_LE(self, op):
        r = self.getvalue(op.result)
        if r.is_constant():
            if r.box.same_constant(CONST_1):
                self.make_int_le(op.getarg(0), op.getarg(1))
            else:
                self.make_int_gt(op.getarg(0), op.getarg(1))

    def propagate_bounds_INT_GE(self, op):
        r = self.getvalue(op.result)
        if r.is_constant():
            if r.box.same_constant(CONST_1):
                self.make_int_ge(op.getarg(0), op.getarg(1))
            else:
                self.make_int_lt(op.getarg(0), op.getarg(1))

    def propagate_bounds_INT_EQ(self, op):
        r = self.getvalue(op.result)
        if r.is_constant():
            if r.box.same_constant(CONST_1):
                v1 = self.getvalue(op.getarg(0))
                v2 = self.getvalue(op.getarg(1))
                if v1.intbound.intersect(v2.intbound):
                    self.propagate_bounds_backward(op.getarg(0))
                if v2.intbound.intersect(v1.intbound):
                    self.propagate_bounds_backward(op.getarg(1))

    def propagate_bounds_INT_NE(self, op):
        r = self.getvalue(op.result)
        if r.is_constant():
            if r.box.same_constant(CONST_0):
                v1 = self.getvalue(op.getarg(0))
                v2 = self.getvalue(op.getarg(1))
                if v1.intbound.intersect(v2.intbound):
                    self.propagate_bounds_backward(op.getarg(0))
                if v2.intbound.intersect(v1.intbound):
                    self.propagate_bounds_backward(op.getarg(1))

    def propagate_bounds_INT_IS_TRUE(self, op):
        r = self.getvalue(op.result)
        if r.is_constant():
            if r.box.same_constant(CONST_1):
                v1 = self.getvalue(op.getarg(0))
                if v1.intbound.known_ge(IntBound(0, 0)):
                    v1.intbound.make_gt(IntBound(0, 0))
                    self.propagate_bounds_backward(op.getarg(0))

    def propagate_bounds_INT_IS_ZERO(self, op):
        r = self.getvalue(op.result)
        if r.is_constant():
            if r.box.same_constant(CONST_1):
                v1 = self.getvalue(op.getarg(0))
                # Clever hack, we can't use self.make_constant_int yet because
                # the args aren't in the values dictionary yet so it runs into
                # an assert, this is a clever way of expressing the same thing.
                v1.intbound.make_ge(IntBound(0, 0))
                v1.intbound.make_lt(IntBound(1, 1))
                self.propagate_bounds_backward(op.getarg(0))

    def propagate_bounds_INT_ADD(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        r = self.getvalue(op.result)
        b = r.intbound.sub_bound(v2.intbound)
        if v1.intbound.intersect(b):
            self.propagate_bounds_backward(op.getarg(0))
        b = r.intbound.sub_bound(v1.intbound)
        if v2.intbound.intersect(b):
            self.propagate_bounds_backward(op.getarg(1))

    def propagate_bounds_INT_SUB(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        r = self.getvalue(op.result)
        b = r.intbound.add_bound(v2.intbound)
        if v1.intbound.intersect(b):
            self.propagate_bounds_backward(op.getarg(0))
        b = r.intbound.sub_bound(v1.intbound).mul(-1)
        if v2.intbound.intersect(b):
            self.propagate_bounds_backward(op.getarg(1))

    def propagate_bounds_INT_MUL(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        r = self.getvalue(op.result)
        b = r.intbound.div_bound(v2.intbound)
        if v1.intbound.intersect(b):
            self.propagate_bounds_backward(op.getarg(0))
        b = r.intbound.div_bound(v1.intbound)
        if v2.intbound.intersect(b):
            self.propagate_bounds_backward(op.getarg(1))

    def propagate_bounds_INT_LSHIFT(self, op):
        v1 = self.getvalue(op.getarg(0))
        v2 = self.getvalue(op.getarg(1))
        r = self.getvalue(op.result)
        b = r.intbound.rshift_bound(v2.intbound)
        if v1.intbound.intersect(b):
            self.propagate_bounds_backward(op.getarg(0))

    propagate_bounds_INT_ADD_OVF  = propagate_bounds_INT_ADD
    propagate_bounds_INT_SUB_OVF  = propagate_bounds_INT_SUB
    propagate_bounds_INT_MUL_OVF  = propagate_bounds_INT_MUL


optimize_ops = _findall(OptIntBounds, 'optimize_')
propagate_bounds_ops = _findall(OptIntBounds, 'propagate_bounds_')

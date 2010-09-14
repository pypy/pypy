from optimizer import Optimization, CONST_1, CONST_0
from pypy.jit.metainterp.optimizeutil import _findall
from pypy.jit.metainterp.optimizeopt.intutils import IntBound, IntUnbounded
from pypy.jit.metainterp.history import Const, ConstInt
from pypy.jit.metainterp.resoperation import rop, ResOperation

class OptIntBounds(Optimization):
    """Keeps track of the bounds placed on integers by the guards and
       remove redundant guards"""

    def propagate_forward(self, op):
        opnum = op.opnum
        for value, func in optimize_ops:
            if opnum == value:
                func(self, op)
                break
        else:
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
        opnum = op.opnum
        for value, func in propagate_bounds_ops:
            if opnum == value:
                func(self, op)
                break
            
    def optimize_GUARD_TRUE(self, op):
        self.emit_operation(op)
        self.propagate_bounds_backward(op.args[0])

    optimize_GUARD_FALSE = optimize_GUARD_TRUE
    optimize_GUARD_VALUE = optimize_GUARD_TRUE

    def optimize_INT_AND(self, op):
        v1 = self.getvalue(op.args[0])
        v2 = self.getvalue(op.args[1])
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
        v1 = self.getvalue(op.args[0])
        v2 = self.getvalue(op.args[1])
        self.emit_operation(op)
        r = self.getvalue(op.result)
        r.intbound.intersect(v1.intbound.sub_bound(v2.intbound))
    
    def optimize_INT_ADD(self, op):
        v1 = self.getvalue(op.args[0])
        v2 = self.getvalue(op.args[1])
        self.emit_operation(op)
        r = self.getvalue(op.result)
        r.intbound.intersect(v1.intbound.add_bound(v2.intbound))

    def optimize_INT_MUL(self, op):
        v1 = self.getvalue(op.args[0])
        v2 = self.getvalue(op.args[1])
        self.emit_operation(op)
        r = self.getvalue(op.result)
        r.intbound.intersect(v1.intbound.mul_bound(v2.intbound))

    def optimize_INT_ADD_OVF(self, op):
        v1 = self.getvalue(op.args[0])
        v2 = self.getvalue(op.args[1])
        resbound = v1.intbound.add_bound(v2.intbound)
        if resbound.has_lower and resbound.has_upper and \
           self.nextop().opnum == rop.GUARD_NO_OVERFLOW:
            # Transform into INT_ADD and remove guard
            op.opnum = rop.INT_ADD
            self.skip_nextop()
            self.optimize_INT_ADD(op)
        else:
            self.emit_operation(op)
            r = self.getvalue(op.result)
            r.intbound.intersect(resbound)
        
    def optimize_INT_SUB_OVF(self, op):
        v1 = self.getvalue(op.args[0])
        v2 = self.getvalue(op.args[1])
        resbound = v1.intbound.sub_bound(v2.intbound)
        if resbound.has_lower and resbound.has_upper and \
               self.nextop().opnum == rop.GUARD_NO_OVERFLOW:
            # Transform into INT_SUB and remove guard
            op.opnum = rop.INT_SUB
            self.skip_nextop()
            self.optimize_INT_SUB(op)
        else:
            self.emit_operation(op)
            r = self.getvalue(op.result)
            r.intbound.intersect(resbound)

    def optimize_INT_MUL_OVF(self, op):
        v1 = self.getvalue(op.args[0])
        v2 = self.getvalue(op.args[1])
        resbound = v1.intbound.mul_bound(v2.intbound)
        if resbound.has_lower and resbound.has_upper and \
               self.nextop().opnum == rop.GUARD_NO_OVERFLOW:
            # Transform into INT_MUL and remove guard
            op.opnum = rop.INT_MUL
            self.skip_nextop()
            self.optimize_INT_MUL(op)
        else:
            self.emit_operation(op)
            r = self.getvalue(op.result)
            r.intbound.intersect(resbound)
        
    def optimize_INT_LT(self, op):
        v1 = self.getvalue(op.args[0])
        v2 = self.getvalue(op.args[1])
        if v1.intbound.known_lt(v2.intbound):
            self.make_constant_int(op.result, 1)
        elif v1.intbound.known_ge(v2.intbound):
            self.make_constant_int(op.result, 0)
        else:
            self.emit_operation(op)

    def optimize_INT_GT(self, op):
        v1 = self.getvalue(op.args[0])
        v2 = self.getvalue(op.args[1])
        if v1.intbound.known_gt(v2.intbound):
            self.make_constant_int(op.result, 1)
        elif v1.intbound.known_le(v2.intbound):
            self.make_constant_int(op.result, 0)
        else:
            self.emit_operation(op)

    def optimize_INT_LE(self, op):
        v1 = self.getvalue(op.args[0])
        v2 = self.getvalue(op.args[1])
        if v1.intbound.known_le(v2.intbound):
            self.make_constant_int(op.result, 1)
        elif v1.intbound.known_gt(v2.intbound):
            self.make_constant_int(op.result, 0)
        else:
            self.emit_operation(op)

    def optimize_INT_GE(self, op):
        v1 = self.getvalue(op.args[0])
        v2 = self.getvalue(op.args[1])
        if v1.intbound.known_ge(v2.intbound):
            self.make_constant_int(op.result, 1)
        elif v1.intbound.known_lt(v2.intbound):
            self.make_constant_int(op.result, 0)
        else:
            self.emit_operation(op)

    def optimize_INT_EQ(self, op):
        v1 = self.getvalue(op.args[0])
        v2 = self.getvalue(op.args[1])
        if v1.intbound.known_gt(v2.intbound):
            self.make_constant_int(op.result, 0)
        elif v1.intbound.known_lt(v2.intbound):
            self.make_constant_int(op.result, 0)
        else: 
            self.emit_operation(op)
            
    def optimize_INT_NE(self, op):
        v1 = self.getvalue(op.args[0])
        v2 = self.getvalue(op.args[1])
        if v1.intbound.known_gt(v2.intbound):
            self.make_constant_int(op.result, 1)
        elif v1.intbound.known_lt(v2.intbound):
            self.make_constant_int(op.result, 1)
        else: 
            self.emit_operation(op)
            
    def make_int_lt(self, args):
        v1 = self.getvalue(args[0])
        v2 = self.getvalue(args[1])
        if v1.intbound.make_lt(v2.intbound):
            self.propagate_bounds_backward(args[0])            
        if v2.intbound.make_gt(v1.intbound):
            self.propagate_bounds_backward(args[1])
        

    def make_int_le(self, args):
        v1 = self.getvalue(args[0])
        v2 = self.getvalue(args[1])
        if v1.intbound.make_le(v2.intbound):
            self.propagate_bounds_backward(args[0])
        if v2.intbound.make_ge(v1.intbound):
            self.propagate_bounds_backward(args[1])

    def make_int_gt(self, args):
        self.make_int_lt([args[1], args[0]])

    def make_int_ge(self, args):
        self.make_int_le([args[1], args[0]])

    def propagate_bounds_INT_LT(self, op):
        r = self.getvalue(op.result)
        if r.is_constant():
            if r.box.same_constant(CONST_1):
                self.make_int_lt(op.args)
            else:
                self.make_int_ge(op.args)

    def propagate_bounds_INT_GT(self, op):
        r = self.getvalue(op.result)
        if r.is_constant():
            if r.box.same_constant(CONST_1):
                self.make_int_gt(op.args)
            else:
                self.make_int_le(op.args)

    def propagate_bounds_INT_LE(self, op):
        r = self.getvalue(op.result)
        if r.is_constant():
            if r.box.same_constant(CONST_1):
                self.make_int_le(op.args)
            else:
                self.make_int_gt(op.args)

    def propagate_bounds_INT_GE(self, op):
        r = self.getvalue(op.result)
        if r.is_constant():
            if r.box.same_constant(CONST_1):
                self.make_int_ge(op.args)
            else:
                self.make_int_lt(op.args)

    def propagate_bounds_INT_EQ(self, op):
        r = self.getvalue(op.result)
        if r.is_constant():
            if r.box.same_constant(CONST_1):
                v1 = self.getvalue(op.args[0])
                v2 = self.getvalue(op.args[1])
                if v1.intbound.intersect(v2.intbound):
                    self.propagate_bounds_backward(op.args[0])
                if v2.intbound.intersect(v1.intbound):
                    self.propagate_bounds_backward(op.args[1])

    def propagate_bounds_INT_NE(self, op):
        r = self.getvalue(op.result)
        if r.is_constant():
            if r.box.same_constant(CONST_0):
                v1 = self.getvalue(op.args[0])
                v2 = self.getvalue(op.args[1])
                if v1.intbound.intersect(v2.intbound):
                    self.propagate_bounds_backward(op.args[0])
                if v2.intbound.intersect(v1.intbound):
                    self.propagate_bounds_backward(op.args[1])

    def propagate_bounds_INT_ADD(self, op):
        v1 = self.getvalue(op.args[0])
        v2 = self.getvalue(op.args[1])
        r = self.getvalue(op.result)
        b = r.intbound.sub_bound(v2.intbound)
        if v1.intbound.intersect(b):
            self.propagate_bounds_backward(op.args[0])    
        b = r.intbound.sub_bound(v1.intbound)
        if v2.intbound.intersect(b):
            self.propagate_bounds_backward(op.args[1])

    def propagate_bounds_INT_SUB(self, op):
        v1 = self.getvalue(op.args[0])
        v2 = self.getvalue(op.args[1])
        r = self.getvalue(op.result)
        b = r.intbound.add_bound(v2.intbound)
        if v1.intbound.intersect(b):
            self.propagate_bounds_backward(op.args[0])        
        b = r.intbound.sub_bound(v1.intbound).mul(-1)
        if v2.intbound.intersect(b):
            self.propagate_bounds_backward(op.args[1])            

    def propagate_bounds_INT_MUL(self, op):
        v1 = self.getvalue(op.args[0])
        v2 = self.getvalue(op.args[1])
        r = self.getvalue(op.result)
        b = r.intbound.div_bound(v2.intbound)
        if v1.intbound.intersect(b):
            self.propagate_bounds_backward(op.args[0])    
        b = r.intbound.div_bound(v1.intbound)
        if v2.intbound.intersect(b):
            self.propagate_bounds_backward(op.args[1])

    propagate_bounds_INT_ADD_OVF  = propagate_bounds_INT_ADD
    propagate_bounds_INT_SUB_OVF  = propagate_bounds_INT_SUB
    propagate_bounds_INT_MUL_OVF  = propagate_bounds_INT_MUL

optimize_ops = _findall(OptIntBounds, 'optimize_')
propagate_bounds_ops = _findall(OptIntBounds, 'propagate_bounds_')
    

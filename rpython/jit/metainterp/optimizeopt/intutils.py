import sys
from rpython.rlib.rarithmetic import ovfcheck, LONG_BIT, maxint, is_valid_int
from rpython.rlib.objectmodel import we_are_translated
from rpython.rtyper.lltypesystem import lltype
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.jit.metainterp.resoperation import rop, ResOperation
from rpython.jit.metainterp.optimizeopt.info import AbstractInfo, INFO_NONNULL,\
     INFO_UNKNOWN, INFO_NULL
from rpython.jit.metainterp.history import ConstInt


MAXINT = maxint
MININT = -maxint - 1

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


class IntBound(AbstractInfo):
    _attrs_ = ('upper', 'lower')

    def __init__(self, lower, upper):
        self.upper = upper
        self.lower = lower
        # check for unexpected overflows:
        if not we_are_translated():
            assert type(upper) is not long or is_valid_int(upper)
            assert type(lower) is not long or is_valid_int(lower)

    # Returns True if the bound was updated
    def make_le(self, other):
        return self.make_le_const(other.upper)

    def make_le_const(self, other):
        if other < self.upper:
            self.upper = other
            return True
        return False

    def make_lt(self, other):
        return self.make_lt_const(other.upper)

    def make_lt_const(self, other):
        try:
            other = ovfcheck(other - 1)
        except OverflowError:
            return False
        return self.make_le_const(other)

    def make_ge(self, other):
        return self.make_ge_const(other.lower)

    def make_ge_const(self, other):
        if other > self.lower:
            self.lower = other
            return True
        return False

    def make_gt_const(self, other):
        try:
            other = ovfcheck(other + 1)
        except OverflowError:
            return False
        return self.make_ge_const(other)

    def make_eq_const(self, intval):
        self.upper = intval
        self.lower = intval

    def make_ne_const(self, intval):
        if self.lower < intval == self.upper:
            self.upper -= 1
            return True
        if self.lower == intval < self.upper:
            self.lower += 1
            return True
        return False

    def make_gt(self, other):
        return self.make_gt_const(other.lower)

    def is_constant(self):
        return self.lower == self.upper

    def get_constant_int(self):
        assert self.is_constant()
        return self.lower

    def equal(self, value):
        if not self.is_constant():
            return False
        return self.lower == value

    def known_lt_const(self, other):
        return self.upper < other

    def known_le_const(self, other):
        return self.upper <= other

    def known_gt_const(self, other):
        return self.lower > other

    def known_ge_const(self, other):
        return self.lower >= other

    def known_lt(self, other):
        return self.known_lt_const(other.lower)

    def known_le(self, other):
        return self.known_le_const(other.lower)

    def known_gt(self, other):
        return other.known_lt(self)

    def known_ge(self, other):
        return other.known_le(self)

    def known_nonnegative(self):
        return 0 <= self.lower

    def intersect(self, other):
        from rpython.jit.metainterp.optimize import InvalidLoop
        if self.known_gt(other) or self.known_lt(other):
            # they don't overlap, which makes the loop invalid
            # this never happens in regular linear traces, but it can happen in
            # combination with unrolling/loop peeling
            raise InvalidLoop("two integer ranges don't overlap")

        r = False
        if self.make_ge_const(other.lower):
            r = True
        if self.make_le_const(other.upper):
            r = True
        return r

    def intersect_const(self, lower, upper):
        r = self.make_ge_const(lower)
        if self.make_le_const(upper):
            r = True
        return r

    def add_bound(self, other):
        """ add two bounds. must be correct even in the presence of possible
        overflows. """
        try:
            lower = ovfcheck(self.lower + other.lower)
        except OverflowError:
            return IntUnbounded()
        try:
            upper = ovfcheck(self.upper + other.upper)
        except OverflowError:
            return IntUnbounded()
        return IntBound(lower, upper)

    def add_bound_cannot_overflow(self, other):
        """ returns True if self + other can never overflow """
        try:
            ovfcheck(self.upper + other.upper)
            ovfcheck(self.lower + other.lower)
        except OverflowError:
            return False
        return True

    def add_bound_no_overflow(self, other):
        """ return the bound that self + other must have, if no overflow occured,
        eg after an int_add_ovf(...), guard_no_overflow() """
        lower = MININT
        try:
            lower = ovfcheck(self.lower + other.lower)
        except OverflowError:
            pass
        upper = MAXINT
        try:
            upper = ovfcheck(self.upper + other.upper)
        except OverflowError:
            pass
        return IntBound(lower, upper)

    def sub_bound(self, other):
        try:
            lower = ovfcheck(self.lower - other.upper)
        except OverflowError:
            return IntUnbounded()
        try:
            upper = ovfcheck(self.upper - other.lower)
        except OverflowError:
            return IntUnbounded()
        return IntBound(lower, upper)

    def sub_bound_cannot_overflow(self, other):
        try:
            ovfcheck(self.lower - other.upper)
            ovfcheck(self.upper - other.lower)
        except OverflowError:
            return False
        return True

    def sub_bound_no_overflow(self, other):
        lower = MININT
        try:
            lower = ovfcheck(self.lower - other.upper)
        except OverflowError:
            pass
        upper = MAXINT
        try:
            upper = ovfcheck(self.upper - other.lower)
        except OverflowError:
            pass
        return IntBound(lower, upper)

    def mul_bound(self, other):
        try:
            vals = (ovfcheck(self.upper * other.upper),
                    ovfcheck(self.upper * other.lower),
                    ovfcheck(self.lower * other.upper),
                    ovfcheck(self.lower * other.lower))
            return IntBound(min4(vals), max4(vals))
        except OverflowError:
            return IntUnbounded()
    mul_bound_no_overflow = mul_bound # can be improved

    def mul_bound_cannot_overflow(self, other):
        try:
            ovfcheck(self.upper * other.upper)
            ovfcheck(self.upper * other.lower)
            ovfcheck(self.lower * other.upper)
            ovfcheck(self.lower * other.lower)
        except OverflowError:
            return False
        return True

    def py_div_bound(self, other):
        if not other.contains(0):
            try:
                # this gives the bounds for 'int_py_div', so use the
                # Python-style handling of negative numbers and not
                # the C-style one
                vals = (ovfcheck(self.upper / other.upper),
                        ovfcheck(self.upper / other.lower),
                        ovfcheck(self.lower / other.upper),
                        ovfcheck(self.lower / other.lower))
                return IntBound(min4(vals), max4(vals))
            except OverflowError:
                pass
        return IntUnbounded()

    def mod_bound(self, other):
        r = IntUnbounded()
        if other.is_constant():
            val = other.get_constant_int()
            if val >= 0:        # with Python's modulo:  0 <= (x % pos) < pos
                r.make_ge_const(0)
                r.make_lt_const(val)
            else:               # with Python's modulo:  neg < (x % neg) <= 0
                r.make_gt_const(val)
                r.make_le_const(0)
        return r

    def lshift_bound(self, other):
        if other.known_nonnegative() and \
           other.known_lt_const(LONG_BIT):
            try:
                vals = (ovfcheck(self.upper << other.upper),
                        ovfcheck(self.upper << other.lower),
                        ovfcheck(self.lower << other.upper),
                        ovfcheck(self.lower << other.lower))
                return IntBound(min4(vals), max4(vals))
            except (OverflowError, ValueError):
                pass
        return IntUnbounded()

    def lshift_bound_cannot_overflow(self, other):
        if other.known_nonnegative() and \
           other.known_lt_const(LONG_BIT):
            try:
                ovfcheck(self.upper << other.upper)
                ovfcheck(self.upper << other.lower)
                ovfcheck(self.lower << other.upper)
                ovfcheck(self.lower << other.lower)
                return True
            except (OverflowError, ValueError):
                pass
        return False


    def rshift_bound(self, other):
        if other.known_nonnegative() and \
           other.known_lt_const(LONG_BIT):
            vals = (self.upper >> other.upper,
                    self.upper >> other.lower,
                    self.lower >> other.upper,
                    self.lower >> other.lower)
            return IntBound(min4(vals), max4(vals))
        else:
            return IntUnbounded()

    def and_bound(self, other):
        pos1 = self.known_nonnegative()
        pos2 = other.known_nonnegative()
        r = IntUnbounded()
        if pos1 or pos2:
            r.make_ge_const(0)
        if pos1:
            r.make_le(self)
        if pos2:
            r.make_le(other)
        return r

    def or_bound(self, other):
        r = IntUnbounded()
        if self.known_nonnegative() and \
                other.known_nonnegative():
            mostsignificant = self.upper | other.upper
            r.intersect(IntBound(0, next_pow2_m1(mostsignificant)))
        return r

    def invert_bound(self):
        upper = ~self.lower
        lower = ~self.upper
        return IntBound(lower, upper)

    def neg_bound(self):
        try:
            upper = ovfcheck(-self.lower)
        except OverflowError:
            return IntUnbounded()
        try:
            lower = ovfcheck(-self.upper)
        except OverflowError:
            return IntUnbounded()
        return IntBound(lower, upper)

    def contains(self, val):
        if not we_are_translated():
            assert not isinstance(val, long)
        if not isinstance(val, int):
            if (self.lower == MININT and self.upper == MAXINT):
                return True # workaround for address as int
        if val < self.lower:
            return False
        if val > self.upper:
            return False
        return True

    def contains_bound(self, other):
        assert isinstance(other, IntBound)
        if not self.contains(other.lower):
            return False
        if not self.contains(other.upper):
            return False
        return True

    def __repr__(self):
        return '%d <= x <= %u' % (self.lower, self.upper)

    def clone(self):
        res = IntBound(self.lower, self.upper)
        return res

    def make_guards(self, box, guards, optimizer):
        if self.is_constant():
            guards.append(ResOperation(rop.GUARD_VALUE,
                                       [box, ConstInt(self.upper)]))
            return
        if self.lower > MININT:
            bound = self.lower
            op = ResOperation(rop.INT_GE, [box, ConstInt(bound)])
            guards.append(op)
            op = ResOperation(rop.GUARD_TRUE, [op])
            guards.append(op)
        if self.upper < MAXINT:
            bound = self.upper
            op = ResOperation(rop.INT_LE, [box, ConstInt(bound)])
            guards.append(op)
            op = ResOperation(rop.GUARD_TRUE, [op])
            guards.append(op)

    def is_bool(self):
        return (self.known_nonnegative() and
                self.known_le_const(1))

    def make_bool(self):
        self.intersect(IntBound(0, 1))

    def getconst(self):
        if not self.is_constant():
            raise Exception("not a constant")
        return ConstInt(self.get_constant_int())

    def getnullness(self):
        if self.known_gt_const(0) or \
           self.known_lt_const(0):
            return INFO_NONNULL
        if self.known_nonnegative() and \
           self.known_le_const(0):
            return INFO_NULL
        return INFO_UNKNOWN

    def widen(self):
        info = self.clone()
        info.widen_update()
        return info

    def widen_update(self):
        if self.lower < MININT / 2:
            self.lower = MININT
        if self.upper > MAXINT / 2:
            self.upper = MAXINT


def IntUpperBound(upper):
    b = IntBound(lower=MININT, upper=upper)
    return b

def IntLowerBound(lower):
    b = IntBound(upper=MAXINT, lower=lower)
    return b

def IntUnbounded():
    return IntBound(MININT, MAXINT)

def ConstIntBound(value):
    return IntBound(value, value)

def min4(t):
    return min(min(t[0], t[1]), min(t[2], t[3]))

def max4(t):
    return max(max(t[0], t[1]), max(t[2], t[3]))

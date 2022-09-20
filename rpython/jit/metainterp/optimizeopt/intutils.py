import sys
from rpython.rlib.rarithmetic import ovfcheck, LONG_BIT, maxint, is_valid_int, r_uint, intmask
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
    _attrs_ = ('has_upper', 'has_lower', 'upper', 'lower', 'tvalue', 'tmask')

    def __init__(self, lower=MININT, upper=MAXINT, 
                 has_lower=False, has_upper=False, 
                 tvalue=0, tmask=-1):
        
        self.has_lower = has_lower
        self.has_upper = has_upper
        self.lower = lower
        self.upper = upper
        
        # known-bit analysis using tristate numbers 
        #  see https://arxiv.org/pdf/2105.05398.pdf
        assert is_valid_tnum(tvalue, tmask)
        self.tvalue = r_uint(tvalue)
        self.tmask = r_uint(tmask)         # bit=1 means unknown

        # check for unexpected overflows:
        if not we_are_translated():
            assert type(upper) is not long or is_valid_int(upper)
            assert type(lower) is not long or is_valid_int(lower)

    def __repr__(self):
        if self.has_lower:
            l = '%d' % self.lower
        else:
            l = '-Inf'
        if self.has_upper:
            u = '%d' % self.upper
        else:
            u = 'Inf'
        return '(%s <= 0b%s <= %s)' % (l, self.knownbits_string(), u)


    # Returns True if the bound was updated
    def make_le(self, other):
        if other.has_upper:
            return self.make_le_const(other.upper)
        return False

    def make_le_const(self, other):
        if not self.has_upper or other < self.upper:
            self.has_upper = True
            self.upper = other
            return True
        return False

    def make_lt(self, other):
        if other.has_upper:
            return self.make_lt_const(other.upper)
        return False

    def make_lt_const(self, other):
        try:
            other = ovfcheck(other - 1)
        except OverflowError:
            return False
        return self.make_le_const(other)

    def make_ge(self, other):
        if other.has_lower:
            return self.make_ge_const(other.lower)
        return False

    def make_ge_const(self, other):
        if not self.has_lower or other > self.lower:
            self.has_lower = True
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
        self.has_upper = True
        self.has_lower = True
        self.upper = intval
        self.lower = intval
        self.tvalue = r_uint(intval)
        self.tmask = r_uint(0)

    def make_gt(self, other):
        if other.has_lower:
            return self.make_gt_const(other.lower)
        return False

    def is_constant_by_bounds(self):
        # for internal use only!
        return self.is_bounded() and (self.lower == self.upper)

    def is_constant_by_knownbits(self):
        # for internal use only!
        return self.tmask == 0

    def is_constant(self):
        return self.is_constant_by_bounds() or self.is_constant_by_knownbits()

    def get_constant_int(self):
        assert self.is_constant()
        if self.is_constant_by_bounds():
            return self.lower
        else:
            return intmask(self.tvalue)

    def is_bounded(self):
        return self.has_lower and self.has_upper

    def equals(self, value):
        if not self.is_constant():
            return False
        if self.is_constant_by_bounds():
            return self.lower == value
        else:
            return r_uint(value) == self.tvalue

    def known_lt_const(self, other):
        if self.has_upper:
            return self.upper < other
        return False

    def known_le_const(self, other):
        if self.has_upper:
            return self.upper <= other
        return False

    def known_gt_const(self, other):
        if self.has_lower:
            return self.lower > other
        return False

    def known_ge_const(self, other):
        if self.has_upper:
            return self.upper >= other
        return False

    def known_lt(self, other):
        if other.has_lower:
            return self.known_lt_const(other.lower)
        return False

    def known_le(self, other):
        if other.has_lower:
            return self.known_le_const(other.lower)
        return False

    def known_gt(self, other):
        return other.known_lt(self)

    def known_ge(self, other):
        return other.known_le(self)

    def known_nonnegative(self):
        return self.has_lower and 0 <= self.lower

    def intersect(self, other):
        r = False
        if other.has_lower:
            if self.make_ge_const(other.lower):
                r = True
        if other.has_upper:
            if self.make_le_const(other.upper):
                r = True

        # tnum stuff.
        union_val = self.tvalue | other.tvalue
        intersect_masks = self.tmask & other.tmask 
        union_masks = self.tmask | other.tmask
        # we assert agreement, e.g. that self and other don't contradict
        unmasked_self = unmask_zero(self.tvalue, union_masks)
        unmasked_other = unmask_zero(other.tvalue, union_masks)
        assert unmasked_self == unmasked_other
        # calculate intersect value and mask
        if self.tmask != intersect_masks:
            self.tvalue = unmask_zero(union_val, intersect_masks)
            self.tmask = intersect_masks
            r = True

        return r

    def intersect_const(self, lower, upper):
        r = self.make_ge_const(lower)
        if self.make_le_const(upper):
            r = True

        return r

    def add(self, offset):
        res = self.clone()
        try:
            res.lower = ovfcheck(res.lower + offset)
        except OverflowError:
            res.has_lower = False
        try:
            res.upper = ovfcheck(res.upper + offset)
        except OverflowError:
            res.has_upper = False
        return res

    def mul(self, value):
        return self.mul_bound(ConstIntBound(value))

    def add_bound(self, other):
        res = self.clone()
        if other.has_upper:
            try:
                res.upper = ovfcheck(res.upper + other.upper)
            except OverflowError:
                res.has_upper = False
        else:
            res.has_upper = False
        if other.has_lower:
            try:
                res.lower = ovfcheck(res.lower + other.lower)
            except OverflowError:
                res.has_lower = False
        else:
            res.has_lower = False
        return res

    def sub_bound(self, other):
        res = self.clone()
        if other.has_lower:
            try:
                res.upper = ovfcheck(res.upper - other.lower)
            except OverflowError:
                res.has_upper = False
        else:
            res.has_upper = False
        if other.has_upper:
            try:
                res.lower = ovfcheck(res.lower - other.upper)
            except OverflowError:
                res.has_lower = False
        else:
            res.has_lower = False
        return res

    def mul_bound(self, other):
        if self.has_upper and self.has_lower and \
           other.has_upper and other.has_lower:
            try:
                vals = (ovfcheck(self.upper * other.upper),
                        ovfcheck(self.upper * other.lower),
                        ovfcheck(self.lower * other.upper),
                        ovfcheck(self.lower * other.lower))
                return IntLowerUpperBound(min4(vals), max4(vals))
            except OverflowError:
                return IntUnbounded()
        else:
            return IntUnbounded()

    def py_div_bound(self, other):
        if self.has_upper and self.has_lower and \
           other.has_upper and other.has_lower and \
           not other.contains(0):
            try:
                # this gives the bounds for 'int_py_div', so use the
                # Python-style handling of negative numbers and not
                # the C-style one
                vals = (ovfcheck(self.upper / other.upper),
                        ovfcheck(self.upper / other.lower),
                        ovfcheck(self.lower / other.upper),
                        ovfcheck(self.lower / other.lower))
                return IntLowerUpperBound(min4(vals), max4(vals))
            except OverflowError:
                return IntUnbounded()
        else:
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
        if self.is_bounded() and other.is_bounded() and \
           other.known_nonnegative() and \
           other.known_lt_const(LONG_BIT):
            try:
                vals = (ovfcheck(self.upper << other.upper),
                        ovfcheck(self.upper << other.lower),
                        ovfcheck(self.lower << other.upper),
                        ovfcheck(self.lower << other.lower))
                return IntLowerUpperBound(min4(vals), max4(vals))
            except (OverflowError, ValueError):
                return IntUnbounded()
        else:
            return IntUnbounded()

    def rshift_bound(self, other):
        if self.is_bounded() and other.is_bounded() and \
           other.known_nonnegative() and \
           other.known_lt_const(LONG_BIT):
            vals = (self.upper >> other.upper,
                    self.upper >> other.lower,
                    self.lower >> other.upper,
                    self.lower >> other.lower)
            return IntLowerUpperBound(min4(vals), max4(vals))
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
        
        self_pmask = self.tvalue | self.tmask
        other_pmask = other.tvalue | other.tmask
        and_vals = self.tvalue & other.tvalue
        r.tvalue = and_vals
        r.tmask = self_pmask & other_pmask & ~and_vals

        return r

    def or_bound(self, other):
        r = IntUnbounded()
        if self.known_nonnegative() and \
                other.known_nonnegative():
            if self.has_upper and other.has_upper:
                mostsignificant = self.upper | other.upper
                r.intersect(IntLowerUpperBound(0, next_pow2_m1(mostsignificant)))
            else:
                r.make_ge_const(0)
        
        union_vals = self.tvalue | other.tvalue
        union_masks = self.tmask | other.tmask
        r.tvalue = union_vals
        r.tmask = union_masks & ~union_vals

        return r

    def xor_bound(self, other):
        r = IntUnbounded()
        if self.known_nonnegative() and \
                other.known_nonnegative():
            if self.has_upper and other.has_upper:
                mostsignificant = self.upper | other.upper
                r.intersect(IntLowerUpperBound(0, next_pow2_m1(mostsignificant)))
            else:
                r.make_ge_const(0)
        
        xor_vals = self.tvalue ^ other.tvalue
        union_masks = self.tmask | other.tmask
        r.tvalue = unmask_zero(xor_vals, union_masks)
        r.tmask = union_masks

        return r

    def invert_bound(self):
        res = self.clone()
        res.has_upper = False
        if self.has_lower:
            res.upper = ~self.lower
            res.has_upper = True
        res.has_lower = False
        if self.has_upper:
            res.lower = ~self.upper
            res.has_lower = True
        return res

    def neg_bound(self):
        res = self.clone()
        res.has_upper = False
        if self.has_lower:
            try:
                res.upper = ovfcheck(-self.lower)
                res.has_upper = True
            except OverflowError:
                pass
        res.has_lower = False
        if self.has_upper:
            try:
                res.lower = ovfcheck(-self.upper)
                res.has_lower = True
            except OverflowError:
                pass
        return res

    def contains(self, val):
        if not we_are_translated():
            assert not isinstance(val, long)
        if not isinstance(val, int):
            if ((not self.has_lower or self.lower == MININT) and
                not self.has_upper or self.upper == MAXINT):
                return True # workaround for address as int
        if self.has_lower and val < self.lower:
            return False
        if self.has_upper and val > self.upper:
            return False
        #import pdb;pdb.set_trace()
        if unmask_zero(self.tvalue, self.tmask) != unmask_zero(r_uint(val), self.tmask):
            return False
        
        return True

    def contains_bound(self, other):
        assert isinstance(other, IntBound)
        if other.has_lower:
            if not self.contains(other.lower):
                return False
        elif self.has_lower:
            return False
        if other.has_upper:
            if not self.contains(other.upper):
                return False
        elif self.has_upper:
            return False
        
        union_masks = self.tmask | other.tmask
        if unmask_zero(self.tvalue, self.tmask) != unmask_zero(other.tvalue, union_masks):
            return False
        
        return True

    def clone(self):
        res = IntLowerUpperBound(self.lower, self.upper)
        res.has_lower = self.has_lower
        res.has_upper = self.has_upper
        return res

    def make_guards(self, box, guards, optimizer):
        if self.is_constant():
            guards.append(ResOperation(rop.GUARD_VALUE,
                                       [box, ConstInt(self.upper)]))
            return
        if self.has_lower and self.lower > MININT:
            bound = self.lower
            op = ResOperation(rop.INT_GE, [box, ConstInt(bound)])
            guards.append(op)
            op = ResOperation(rop.GUARD_TRUE, [op])
            guards.append(op)
        if self.has_upper and self.upper < MAXINT:
            bound = self.upper
            op = ResOperation(rop.INT_LE, [box, ConstInt(bound)])
            guards.append(op)
            op = ResOperation(rop.GUARD_TRUE, [op])
            guards.append(op)

    def is_bool(self):
        return (self.is_bounded() and self.known_nonnegative() and
                self.known_le_const(1))

    def make_bool(self):
        self.intersect(IntLowerUpperBound(0, 1))

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

    """def internal_intersect():
        # synchronizes bounds and knownbits values
        # this does most likely not cover edge cases like overflows
        def sync_ktb_min():
            # transcribes from knownbits to bounds minimum
            t_minimum = unmask_zero(self.tvalue, self.tmask)
            # set negative iff msb unknown or 1
            t_minimum |= msbonly(self.tvalue) | msbonly(self.tmask)
            self.lower = t_minimum
        def sync_ktb_max():
            # transcribes from knownbits to bounds maximum
            t_maximum = unmask_one(self.tvalue, self.tmask)
            # set positive iff msb unknown or 0
            t_maximum &= ~(~msbonly(self.tvalue) | msbonly(self.tmask))
            self.upper = t_maximum
        def sync_btk():
            # transcribes from bounds to knownbits"""
            


    def knownbits_string(self, unk_sym = '?'):
        results = []
        for bit in range(LONG_BIT):
            if self.tmask & (1 << bit):
                results.append(unk_sym)
            else:
                results.append(str((self.tvalue >> bit) & 1))
        results.reverse()
        return "".join(results)


def IntLowerUpperBound(lower, upper):
    b = IntBound(lower=lower, 
                 upper=upper,
                 has_lower=True,
                 has_upper=True)
    return b

def IntUpperBound(upper):
    b = IntBound(lower=0, 
                 upper=upper,
                 has_lower=False,
                 has_upper=True)
    return b

def IntLowerBound(lower):
    b = IntBound(lower=lower,
                 upper=0, 
                 has_lower=True,
                 has_upper=False)
    return b

def IntUnbounded():
    b = IntBound(lower=0, 
                 upper=0, 
                 has_lower=False, 
                 has_upper=False)
    return b

def ConstIntBound(value):
    tvalue = value
    tmask = 0
    if not isinstance(value, int):
        # AddressAsInt
        tvalue = 0
        tmask = -1
    b = IntBound(lower=value, 
                 upper=value,
                 has_lower=True,
                 has_upper=True,
                 tvalue=tvalue,
                 tmask=tmask)
    return b

def IntBoundKnownbits(value, mask):
    b = IntBound(lower=0, 
                 upper=0, 
                 has_lower=False, 
                 has_upper=False,
                 tvalue=value,
                 tmask=mask)
    return b

def unmask_zero(value, mask):
    # sets all unknowns in value to 0
    return value & ~mask

def unmask_one(value, mask):
    # sets all unknowns in value to 1
    return value | mask

def min4(t):
    return min(min(t[0], t[1]), min(t[2], t[3]))

def max4(t):
    return max(max(t[0], t[1]), max(t[2], t[3]))

def msbonly(v):
    return v & (1 << LONG_BIT)

def is_valid_tnum(tvalue, tmask):
    return 0 == (r_uint(tvalue) & r_uint(tmask))

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

TNUM_UNKNOWN = r_uint(0), r_uint(-1)
TNUM_KNOWN_ZERO = r_uint(0), r_uint(0)
TNUM_KNOWN_BITWISEONE = r_uint(-1), r_uint(0)
TNUM_ONLY_VALUE_DEFAULT = r_uint(0)
TNUM_ONLY_MASK_UNKNOWN = r_uint(-1)
TNUM_ONLY_MASK_DEFAULT = TNUM_ONLY_MASK_UNKNOWN

def next_pow2_m1(n):
    """Calculate next power of 2 minus one, greater than n"""
    n |= n >> 1
    n |= n >> 2
    n |= n >> 4
    n |= n >> 8
    n |= n >> 16
    if IS_64_BIT:
        n |= n >> 32
    return n

def leading_zeros_mask(n):
    """
    calculates a bitmask in which only the leading zeros
    of `n` are set (1).
    """
    assert isinstance(n, r_uint)
    if n == MAXINT:
        return r_uint(0)
    else:
        return ~next_pow2_m1(n+1)

class IntBound(AbstractInfo):
    """
    Abstract domain representation of an integer,
    approximating via integer bounds and known-bits
    tri-state numbers.
    """
    _attrs_ = ('upper', 'lower', 'tvalue', 'tmask')

    def __init__(self, lower=MININT, upper=MAXINT,
                 tvalue=TNUM_ONLY_VALUE_DEFAULT,
                 tmask=TNUM_ONLY_MASK_DEFAULT):
        """
        It is recommended to use the indirect constructors
        below instead of this one.
        Instantiates an abstract representation of integer.
        The default parameters set this abstract int to
        contain all integers.
        """

        self.lower = lower
        self.upper = upper

        # known-bit analysis using tristate numbers
        #  see https://arxiv.org/pdf/2105.05398.pdf
        assert is_valid_tnum(tvalue, tmask)
        self.tvalue = tvalue
        self.tmask = tmask         # bit=1 means unknown
        self.shrink_bounds_by_knownbits()
        #if lower == 0 and upper == 0:
        #    import pdb; pdb.set_trace()
        self.shrink_knownbits_by_bounds()

        # check for unexpected overflows:
        if not we_are_translated():
            assert type(upper) is not long or is_valid_int(upper)
            assert type(lower) is not long or is_valid_int(lower)

        assert self.knownbits_and_bounds_agree()

    def __repr__(self):
        l = self.lower
        u = self.upper
        return '(%s <= 0b%s <= %s)' % (l, self.knownbits_string(), u)

    def make_le(self, other):
        """
        Sets the bounds of `self` so that it only
        contains values lower than or equal to the
        values contained in `other`.
        Returns `True` iff the bound was updated.
        (Mutates `self`.)
        """
        return self.make_le_const(other.upper)

    def make_le_const(self, value):
        """
        Sets the bounds of `self` so that it
        only contains values lower than or equal
        to `value`.
        Returns `True` iff the bound was updated.
        (Mutates `self`.)
        """
        if value < self.upper:
            self.upper = value
            return True
        return False

    def make_lt(self, other):
        """
        Sets the bounds of `self` so that it
        only contains values lower than the values
        contained in `other`.
        Returns `True` iff the bound was updated.
        (Mutates `self`.)
        """
        return self.make_lt_const(other.upper)

    def make_lt_const(self, value):
        """
        Sets the bounds of `self` so that it
        only contains values lower than `value`.
        Returns `True` iff the bound was updated.
        (Mutates `self`.)
        """
        try:
            value = ovfcheck(value - 1)
        except OverflowError:
            return False
        return self.make_le_const(value)

    def make_ge(self, other):
        """
        Sets the bounds of `self` so that it only
        contains values greater than or equal to the
        values contained in `other`.
        Returns `True` iff the bound was updated.
        (Mutates `self`.)
        """
        return self.make_ge_const(other.lower)

    def make_ge_const(self, value):
        """
        Sets the bounds of `self` so that it
        only contains values greater than or equal
        to `value`.
        Returns `True` iff the bound was updated.
        (Mutates `self`.)
        """
        if value > self.lower:
            self.lower = value
            return True
        return False

    def make_gt(self, other):
        """
        Sets the bounds of `self` so that it
        only contains values greater than the values
        contained in `other`.
        Returns `True` iff the bound was updated.
        (Mutates `self`.)
        """
        return self.make_gt_const(other.lower)

    def make_gt_const(self, value):
        """
        Sets the bounds of `self` so that it
        only contains values greater than `value`.
        Returns `True` iff the bound was updated.
        (Mutates `self`.)
        """
        try:
            value = ovfcheck(value + 1)
        except OverflowError:
            return False
        return self.make_ge_const(value)

    def make_eq_const(self, intval):
        """
        Sets the properties of this abstract integer
        so that it is constant and equals `intval`.
        (Mutates `self`.)
        """
        self.upper = intval
        self.lower = intval
        self.tvalue = r_uint(intval)
        self.tmask = r_uint(0)

    def make_ne_const(self, intval):
        if self.lower < intval == self.upper:
            self.upper -= 1
            return True
        if self.lower == intval < self.upper:
            self.lower += 1
            return True
        return False

    def is_constant_by_bounds(self):
        """ for internal use only! """
        return self.lower == self.upper

    def is_constant_by_knownbits(self):
        """ for internal use only! """
        return self.tmask == 0

    def is_constant(self):
        """
        Returns `True` iff this abstract integer
        does contain only one (1) concrete integer.
        """
        return self.is_constant_by_bounds() or \
               self.is_constant_by_knownbits()

    def get_constant_int(self):
        """
        Returns the only integer contained in this
        abstract integer, asserting that it
        `is_constant()`.
        """
        assert self.is_constant()
        if self.is_constant_by_bounds():
            return self.lower
        else:  # is_constant_by_knownbits
            return intmask(self.tvalue)

    def equals(self, value):
        """
        Returns `True` iff this abstract integer
        contains only one (1) integer that does
        equal `value`.
        """
        if not self.is_constant():
            return False
        if self.is_constant_by_bounds():
            return self.lower == value
        else:
            return r_uint(value) == self.tvalue

    def known_lt_const(self, value):
        """
        Returns `True` iff each number contained
        in this abstract integer is lower than
        `value`.
        """
        return self.upper < value

    def known_le_const(self, value):
        """
        Returns `True` iff each number contained
        in this abstract integer is lower than
        or equal to `value`.
        """
        return self.upper <= value

    def known_gt_const(self, value):
        """
        Returns `True` iff each number contained
        in this abstract integer is greater than
        `value`.
        """
        return self.lower > value

    def known_ge_const(self, value):
        """
        Returns `True` iff each number contained
        in this abstract integer is greater than
        equal to `value`.
        """
        return self.lower >= value

    def known_lt(self, other):
        """
        Returns `True` iff each number contained
        in this abstract integer is lower than
        each integer contained in `other`.
        """
        return self.known_lt_const(other.lower)

    def known_le(self, other):
        """
        Returns `True` iff each number contained
        in this abstract integer is lower than
        or equal to each integer contained in
        `other`.
        """
        return self.known_le_const(other.lower)

    def known_gt(self, other):
        """
        Returns `True` iff each number contained
        in this abstract integer is greater than
        each integer contained in `other`.
        """
        return other.known_lt(self)

    def known_ge(self, other):
        """
        Returns `True` iff each number contained
        in this abstract integer is greater than
        or equal to each integer contained in
        `other`.
        """
        return other.known_le(self)

    def known_nonnegative(self):
        """
        Returns `True` if this abstract integer
        only contains numbers greater than or
        equal to `0` (zero).
        """
        return 0 <= self.lower

    def known_nonnegative_by_bounds(self):
        """ for internal use only! """
        # Returns `True` if this abstract integer
        # only contains numbers greater than or
        # equal to `0` (zero), IGNORING KNOWNBITS.
        minest = self.get_minimum_estimation_signed()
        return 0 <= minest

    def get_minimum_signed_by_knownbits(self):
        """ for internal use only! """
        return intmask(self.tvalue | msbonly(self.tmask))

    def get_maximum_signed_by_knownbits(self):
        """ for internal use only! """
        unsigned_mask = self.tmask & ~msbonly(self.tmask)
        return intmask(self.tvalue | unsigned_mask)

    def get_minimum_signed(self):
        ret_k = r_uint(self.get_minimum_signed_by_knownbits())
        ret_b = r_uint(self.minimum)
        if ret_k >= ret_b:
            ret = ret_k
        else:
            ret = ret_k
            while ret < ret_b:
                pass
                # binary search? what about backtracking?
        return ret

    def get_maximum_signed(self):
        return -self.neg_bound().get_minimum_signed()

    def get_minimum_estimation_signed(self):
        """
        Returns an estimated lower bound for
        the numbers contained in this
        abstract integer.
        It is not guaranteed that this value
        is actually an element of the
        concrete value set!
        """
        # Unnecessary to unmask, because by convention
        #   mask[i] => ~value[i]
        ret_knownbits = self.get_minimum_signed_by_knownbits()
        ret_bounds = self.lower
        return max(ret_knownbits, ret_bounds)

    def get_maximum_estimation_signed(self):
        """
        Returns an estimated upper bound for
        the numbers contained in this
        abstract integer.
        It is not guaranteed that this value
        is actually an element of the
        concrete value set!
        """
        ret_knownbits = self.get_maximum_signed_by_knownbits()
        ret_bounds = self.upper
        return min(ret_knownbits, ret_bounds)

    def intersect(self, other):
        """
        Mutates `self` so that it contains
        integers that are contained in `self`
        and `other`, and only those.
        Basically intersection of sets.
        Throws errors if `self` and `other`
        "disagree", meaning the result would
        contain 0 (zero) any integers.
        """
        assert not self.known_gt(other) and not self.known_lt(other)

        r = False
        if self.make_ge_const(other.lower):
            r = True
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

        # we also assert agreement between knownbits and bounds
        assert self.knownbits_and_bounds_agree()
        return r

    def intersect_const(self, lower, upper):
        """
        Mutates `self` so that it contains
        integers that are contained in `self`
        and the range [`lower`, `upper`],
        and only those.
        Basically intersection of sets.
        Does only affect the bounds, so if
        possible the use of the `intersect`
        function is recommended instead.
        """
        r = self.make_ge_const(lower)
        if self.make_le_const(upper):
            r = True

        return r

    def add(self, value):
        return self.add_bound(ConstIntBound(value))

    def add_bound(self, other):
        """
        Adds the `other` abstract integer to
        `self` and returns the result.
        Must be correct in the presence of possible overflows.
        (Does not mutate `self`.)
        """

        sum_values = self.tvalue + other.tvalue
        sum_masks = self.tmask + other.tmask
        all_carries = sum_values + sum_masks
        val_carries = all_carries ^ sum_values
        tmask = self.tmask | other.tmask | val_carries
        tvalue = unmask_zero(sum_values, tmask)

        try:
            lower = ovfcheck(self.lower + other.lower)
        except OverflowError:
            return IntBound(tvalue=tvalue, tmask=tmask)
        try:
            upper = ovfcheck(self.upper + other.upper)
        except OverflowError:
            return IntBound(tvalue=tvalue, tmask=tmask)
        return IntBound(lower, upper, tvalue, tmask)

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
        res = self.add_bound(other)

        # returning add_bound is always correct, but let's improve the range
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
        res.lower = lower
        res.upper = upper
        return res

    def sub_bound(self, other):
        """
        Subtracts the `other` abstract
        integer from `self` and returns the
        result.
        (Does not mutate `self`.)
        """
        res = self.add_bound(other.neg_bound())
        return res

    def sub_bound_cannot_overflow(self, other):
        try:
            ovfcheck(self.lower - other.upper)
            ovfcheck(self.upper - other.lower)
        except OverflowError:
            return False
        return True

    def sub_bound_no_overflow(self, other):
        res = self.sub_bound(other)
        # returning sub_bound is always correct, but let's improve the range
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
        res.lower = lower
        res.upper = upper
        return res

    def mul_bound(self, other):
        """
        Multiplies the `other` abstract
        integer with `self` and returns the
        result.
        (Does not mutate `self`.)
        """
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
        """
        Divides this abstract integer by the
        `other` abstract integer and returns
        the result.
        (Does not mutate `self`.)
        """
        if not other.contains(0):
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
                pass
        return IntUnbounded()

    def mod_bound(self, other):
        """
        Calculates the mod of this abstract
        integer by the `other` abstract
        integer and returns the result.
        (Does not mutate `self`.)
        """
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
        """
        Shifts this abstract integer `other`
        bits to the left, where `other` is
        another abstract integer.
        (Does not mutate `self`.)
        """

        tvalue, tmask = TNUM_UNKNOWN
        if other.is_constant():
            c_other = other.get_constant_int()
            if c_other >= LONG_BIT:
                 tvalue, tmask = TNUM_KNOWN_ZERO
            elif 0 <= c_other < LONG_BIT:
                tvalue = self.tvalue << r_uint(c_other)
                tmask = self.tmask << r_uint(c_other)
            # else: bits are unknown because arguments invalid

        if other.known_nonnegative() and other.known_lt_const(LONG_BIT):
            try:
                vals = (ovfcheck(self.upper << other.upper),
                        ovfcheck(self.upper << other.lower),
                        ovfcheck(self.lower << other.upper),
                        ovfcheck(self.lower << other.lower))
                return IntBound(min4(vals), max4(vals), tvalue, tmask)
            except (OverflowError, ValueError):
                pass

        return IntBoundKnownbits(tvalue, tmask)

    def rshift_bound(self, other):
        """
        Shifts this abstract integer `other`
        bits to the right, where `other` is
        another abstract integer, and extends
        its sign.
        (Does not mutate `self`.)
        """

        # this seems to always be the signed variant..?
        tvalue, tmask = TNUM_UNKNOWN
        if other.is_constant():
            c_other = other.get_constant_int()
            if c_other >= LONG_BIT:
                # shift value out to the right, but do sign extend
                if msbonly(self.tmask): # sign-extend mask
                    tvalue, tmask = TNUM_UNKNOWN
                elif msbonly(self.tvalue): # sign-extend value
                    tvalue, tmask = TNUM_KNOWN_BITWISEONE
                else: # sign is 0 on both
                    tvalue, tmask = TNUM_KNOWN_ZERO
            elif c_other >= 0:
                # we leverage native sign extension logic
                tvalue = r_uint(intmask(self.tvalue) >> c_other)
                tmask = r_uint(intmask(self.tmask) >> c_other)
            # else: bits are unknown because arguments invalid

        lower = MININT
        upper = MAXINT
        if other.known_nonnegative() and other.known_lt_const(LONG_BIT):
            vals = (self.upper >> other.upper,
                    self.upper >> other.lower,
                    self.lower >> other.upper,
                    self.lower >> other.lower)
            lower = min4(vals)
            upper = max4(vals)
        return IntBound(lower, upper, tvalue, tmask)

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


    def urshift_bound(self, other):
        """
        Shifts this abstract integer `other`
        bits to the right, where `other` is
        another abstract integer, *without*
        extending its sign.
        (Does not mutate `self`.)
        """

        # this seems to always be the signed variant..?
        tvalue, tmask = TNUM_UNKNOWN
        if other.is_constant():
            c_other = other.get_constant_int()
            if c_other >= LONG_BIT:
                # no sign to extend, we get constant 0
                tvalue, tmask = TNUM_KNOWN_ZERO
            elif c_other >= 0:
                tvalue = self.tvalue >> r_uint(c_other)
                tmask = self.tmask >> r_uint(c_other)
            # else: bits are unknown because arguments invalid

        # we don't do bounds on unsigned
        return IntBoundKnownbits(tvalue, tmask)

    def and_bound(self, other):
        """
        Performs bit-wise AND of this
        abstract integer and the `other`,
        returning its result.
        (Does not mutate `self`.)
        """

        pos1 = self.known_nonnegative_by_bounds()
        pos2 = other.known_nonnegative_by_bounds()
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
        """
        Performs bit-wise OR of this
        abstract integer and the `other`,
        returning its result.
        (Does not mutate `self`.)
        """

        lower = MININT
        upper = MAXINT
        if self.known_nonnegative_by_bounds() and \
                other.known_nonnegative_by_bounds():
            mostsignificant = self.upper | other.upper
            lower = 0
            upper = next_pow2_m1(mostsignificant)

        union_vals = self.tvalue | other.tvalue
        union_masks = self.tmask | other.tmask
        tvalue = union_vals
        tmask = union_masks & ~union_vals

        return IntBound(lower, upper, tvalue, tmask)

    def xor_bound(self, other):
        """
        Performs bit-wise XOR of this
        abstract integer and the `other`,
        returning its result.
        (Does not mutate `self`.)
        """

        lower = MININT
        upper = MAXINT
        if self.known_nonnegative_by_bounds() and \
                other.known_nonnegative_by_bounds():
            mostsignificant = self.upper | other.upper
            lower = 0
            upper = next_pow2_m1(mostsignificant)

        xor_vals = self.tvalue ^ other.tvalue
        union_masks = self.tmask | other.tmask
        tvalue = unmask_zero(xor_vals, union_masks)
        tmask = union_masks

        return IntBound(lower, upper, tvalue, tmask)

    def neg_bound(self):
        """
        Arithmetically negates this abstract
        integer and returns the result.
        (Does not mutate `self`.)
        """
        res = self.invert_bound()
        res = res.add_bound(ConstIntBound(1))
        return res

    def invert_bound(self):
        """
        Performs bit-wise NOT on this
        abstract integer returning its
        result.
        (Does not mutate `self`.)
        """
        upper = ~self.lower
        lower = ~self.upper
        tvalue = unmask_zero(~self.tvalue, self.tmask)
        tmask = self.tmask
        return IntBound(lower, upper, tvalue, tmask)

    def contains(self, val):
        """
        Returns `True` iff this abstract
        integer contains the given `val`ue.
        """

        assert not isinstance(val, IntBound)

        if not we_are_translated():
            assert not isinstance(val, long)
        if not isinstance(val, int):
            if (self.lower == MININT and self.upper == MAXINT):
                return True # workaround for address as int
        if val < self.lower:
            return False
        if val > self.upper:
            return False

        u_vself = unmask_zero(self.tvalue, self.tmask)
        u_value = unmask_zero(r_uint(val), self.tmask)
        if u_vself != u_value:
            return False

        return True

    def contains_bound(self, other):
        """
        ???
        """
        assert isinstance(other, IntBound)

        # TODO: think about every caller
        assert (self.tvalue, self.tmask) == TNUM_UNKNOWN

        if not self.contains(other.lower):
            return False
        if not self.contains(other.upper):
            return False

        # not relevant at the moment
        """union_masks = self.tmask | other.tmask
        if unmask_zero(self.tvalue, self.tmask) != unmask_zero(other.tvalue, union_masks):
            return False"""

        return True

    def clone(self):
        """
        Returns an exact copy of this
        abstract integer.
        """
        res = IntBound(self.lower, self.upper,
                       self.tvalue, self.tmask)
        return res

    def make_guards(self, box, guards, optimizer):
        """
        Generates guards from the information
        we have about the numbers this
        abstract integer contains.
        """
        # TODO
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
        """
        Returns `True` iff the properties
        of this abstract integer allow it to
        represent a conventional boolean
        value.
        """
        return (self.known_nonnegative() and self.known_le_const(1))

    def make_bool(self):
        """
        Mutates this abstract integer so that
        it does represent a conventional
        boolean value.
        (Mutates `self`.)
        """
        self.intersect(IntLowerUpperBound(0, 1))

    def getconst(self):
        """
        Returns an abstract integer that
        equals the value of this abstract
        integer if it is constant, otherwise
        throws an Exception.
        """
        if not self.is_constant():
            raise Exception("not a constant")
        return ConstInt(self.get_constant_int())

    def getnullness(self):
        """
        Returns information about whether
        this this abstract integer is known
        to be zero or not to be zero.
        """
        if self.known_gt_const(0) or \
           self.known_lt_const(0) or \
           self.tvalue != 0:
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
        self.tvalue, self.tmask = TNUM_UNKNOWN


    def and_bound_backwards(self, other, result_int):
        """
        result_int == int_and(self, other)
        We want to refine our knowledge about self
        using this information

        regular &:
                  other
         &  0   1   ?
         0  0   0   0
         1  0   1   ?
         ?  0   ?   ?   <- result
        self

        backwards & (this one):
                  other
            0   1   ?
         0  ?   0   ?
         1  X?  1   ?
         ?  ?   ?   ?   <- self
        result

        If the knownbits of self and result are inconsistent,
        the values of result are used (this must not happen
        in practice and will be caught by an assert in intersect())
        """

        tvalue = self.tvalue
        tmask = self.tmask
        tvalue &= ~other.tvalue | other.tmask
        tvalue |= r_uint(result_int) & other.tvalue
        tmask &= ~other.tvalue | other.tmask
        return IntBoundKnownbits(tvalue, tmask)

    def or_bound_backwards(self, other, result_int):
        """
        result_int == int_or(self, other)
        We want to refine our knowledge about self
        using this information

        regular |:
                  other
         &  0   1   ?
         0  0   1   ?
         1  1   1   ?
         ?  ?   ?   ?   <- result
        self

        backwards | (this one):
                  other
            0   1   ?
         0  0   X?  X0
         1  1   ?   ?
         ?  ?   ?   ?   <- self (where X=invalid)
        result

        For every X just go ?.
        If the knownbits of self and result are inconsistent,
        the values of result are used (this must not happen
        in practice and will be caught by an assert in intersect())
        """
        pass

    def urshift_bound_backwards(self, other, result):
        """
        Performs a `urshift` backwards on
        `result`. Basically left-shifts
        `result` by `other` binary digits,
        filling the lower part with ?, and
        returns the result.
        """
        if not other.is_constant():
            return IntUnbounded()
        c_other = other.get_constant_int()
        tvalue, tmask = TNUM_UNKNOWN
        if 0 <= c_other < LONG_BIT:
            tvalue = result.tvalue << r_uint(c_other)
            tmask = result.tmask << r_uint(c_other)
            # shift ? in from the right,
            # but we know some bits from `self`
            s_tmask = (r_uint(1) << r_uint(c_other)) - 1
            s_tvalue = s_tmask & self.tvalue
            s_tmask &= self.tmask
            tvalue |= s_tvalue
            tmask |= s_tmask
        # ignore bounds # TODO: bounds
        return IntBoundKnownbits(tvalue, tmask)

    def rshift_bound_backwards(self, other, result):
        """
        Performs a `rshift` backwards on
        `result`. Basically left-shifts
        `result` by `other` binary digits,
        filling the lower part with ?, and
        returns the result.
        """
        # left shift is the reverse function of
        # both urshift and rshift.
        return self.urshift_bound_backwards(other, result)


    def shrink_bounds_by_knownbits(self):
        """
        Shrinks the bounds by the known bits.
        """
        min_by_knownbits = self.get_minimum_signed_by_knownbits()
        if min_by_knownbits > self.lower:
            self.lower = min_by_knownbits
        max_by_knownbits = self.get_maximum_signed_by_knownbits()
        if max_by_knownbits < self.upper:
            self.upper = max_by_knownbits

    def shrink_knownbits_by_bounds(self):
        """
        Infers known bits from the bounds.
        Basically fills a common prefix
        from lower and upper bound into
        the knownbits.
        """
        #import pdb; pdb.set_trace()
        # are we working on negative or positive values?
        # get the working values
        if (self.lower >= 0) != (self.upper >= 0):
            # nothing to do if signs are different
            # this should actually not be necessary,
            # but remains as a safe guard
            return
        # calculate higher bit mask by bounds
        work_lower = r_uint(self.lower)
        work_upper = r_uint(self.upper)
        hbm_bounds = leading_zeros_mask(work_lower ^ work_upper)
        bounds_common = work_lower & hbm_bounds
        # we can assert agreement between bounds and knownbits here!
        assert unmask_zero(bounds_common, self.tmask) == (self.tvalue & hbm_bounds)
        hbm = hbm_bounds & self.tmask
        # apply the higher bit mask to the knownbits
        self.tmask &= ~hbm  # make bits known
        self.tvalue = (bounds_common & hbm) | (self.tvalue & ~hbm)

    def knownbits_and_bounds_agree(self):
        """
        Returns `True` iff the span of
        knownbits and the span of the bounds
        have a non-empty intersection.
        That does not guarantee for the
        actual concrete value set to contain
        any values!
        """
        max_knownbits = self.get_maximum_signed_by_knownbits()
        if not max_knownbits >= self.lower:
            return False
        min_knownbits = self.get_minimum_signed_by_knownbits()
        if not min_knownbits <= self.upper:
            return False
        return True

    def knownbits_string(self, unk_sym = '?'):
        """
        Returns a beautiful string
        representation about the knownbits
        part of this abstract integer.
        You can give any symbol or string
        for the "unknown bits"
        (default: '?'), the other digits are
        written as '1' and '0'.
        """
        results = []
        for bit in range(LONG_BIT):
            if self.tmask & (1 << bit):
                results.append(unk_sym)
            else:
                results.append(str((self.tvalue >> bit) & 1))
        results.reverse()
        return "".join(results)


def IntLowerUpperBound(lower, upper):
    """
    Constructs an abstract integer that is
    greater than or equal to `lower` and
    lower than or equal to `upper`, e.g.
    it is bound by `lower` and `upper`.
    """
    return IntBound(lower=lower,
                    upper=upper)

def IntUpperBound(upper):
    """
    Constructs an abstract integer that is
    lower than or equal to `upper`, e.g.
    it is bound by `upper`.
    """
    return IntBound(upper=upper)

def IntLowerBound(lower):
    """
    Constructs an abstract integer that is
    greater than or equal to `lower`, e.g.
    it is bound by `lower`.
    """
    return IntBound(lower=lower)

def IntUnbounded():
    """
    Constructs an abstract integer that is
    completely unknown (e.g. it contains
    every integer).
    """
    return IntBound()

def ConstIntBound(value):
    """
    Constructs an abstract integer that
    represents a constant (a completely
    known integer).
    """
    # this one does NOT require a r_uint for `value`.
    assert not isinstance(value, r_uint)
    tvalue = value
    tmask = 0
    bvalue = value
    if not isinstance(value, int):
        # workaround for AddressAsInt / symbolic ints
        # by CF
        tvalue = 0
        tmask = -1
        bvalue = 0
    b = IntBound(lower=bvalue,
                 upper=bvalue,
                 tvalue=r_uint(tvalue),
                 tmask=r_uint(tmask))
    return b

def IntBoundKnownbits(value, mask, do_unmask=False):
    """
    Constructs an abstract integer where the
    bits determined by `value` and `mask` are
    (un-)known.
    Requires an `r_uint` for `value` and
    `mask`!
    """
    # this one does require a r_uint for `value` and `mask`.
    assert isinstance(value, r_uint) and isinstance(mask, r_uint)
    if do_unmask:
        value = unmask_zero(value, mask)
    b = IntBound(tvalue=value,
                 tmask=mask)
    return b

def IntLowerUpperBoundKnownbits(lower, upper, value, mask, do_unmask=False):
    """
    Constructs an abstract integer that
    is bound by `lower` and `upper`, where
    the bits determined by `value` and `mask`
    are (un-)known.
    Requires an `r_uint` for `value` and
    `mask`!
    """
    # this one does require a r_uint for `value` and `mask`.
    assert isinstance(value, r_uint) and isinstance(mask, r_uint)
    if do_unmask:
        value = unmask_zero(value, mask)
    b = IntBound(lower=lower,
                 upper=upper,
                 tvalue=value,
                 tmask=mask)
    return b

def unmask_zero(value, mask):
    """
    Sets all unknowns determined by
    `mask` in `value` bit-wise to 0 (zero)
    and returns the result.
    """
    return value & ~mask

def unmask_one(value, mask):
    """
    Sets all unknowns determined by
    `mask` in `value` bit-wise to 1 (one)
    and returns the result.
    """
    return value | mask

def min4(t):
    """
    Returns the minimum of the values in
    the quadruplet t.
    """
    return min(min(t[0], t[1]), min(t[2], t[3]))

def max4(t):
    """
    Returns the maximum of the values in
    the quadruplet t.
    """
    return max(max(t[0], t[1]), max(t[2], t[3]))

def msbonly(v):
    """
    Returns `v` with all bits except the
    most significant bit set to 0 (zero).
    """
    return v & (1 << (LONG_BIT-1))

def is_valid_tnum(tvalue, tmask):
    """
    Returns `True` iff `tvalue` and `tmask`
    would be valid tri-state number fields
    of an abstract integer, meeting all
    conventions and requirements.
    """
    if not isinstance(tvalue, r_uint):
        return False
    if not isinstance(tmask, r_uint):
        return False
    return 0 == (r_uint(tvalue) & r_uint(tmask))

def lowest_set_bit_only(val_uint):
    """
    Returns an val_int, but with all bits
    deleted but the lowest one that was set.
    """
    assert isinstance(val_uint, r_uint)
    working_val = ~val_uint
    increased_val = working_val + 1
    result = (working_val^increased_val) & ~working_val
    return result

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
    """
    Abstract domain representation of an integer,
    approximating via integer bounds and known-bits
    tri-state numbers.
    """
    _attrs_ = ('has_upper', 'has_lower', 'upper', 'lower', 'tvalue', 'tmask')

    def __init__(self, lower=MININT, upper=MAXINT,
                 has_lower=False, has_upper=False,
                 tvalue=TNUM_ONLY_VALUE_DEFAULT,
                 tmask=TNUM_ONLY_MASK_DEFAULT):
        """
        It is recommended to use the indirect constructors
        below instead of this one.
        Instantiates an abstract representation of integer.
        The default parameters set this abstract int to
        contain all integers.
        """

        self.has_lower = has_lower
        self.has_upper = has_upper
        self.lower = lower
        self.upper = upper

        # known-bit analysis using tristate numbers
        #  see https://arxiv.org/pdf/2105.05398.pdf
        assert is_valid_tnum(tvalue, tmask)
        self.tvalue = tvalue
        self.tmask = tmask         # bit=1 means unknown

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


    def make_le(self, other):
        """
        Sets the bounds of `self` so that it only
        contains values lower than or equal to the
        values contained in `other`.
        Returns `True` iff the bound was updated.
        (Mutates `self`.)
        """
        if other.has_upper:
            return self.make_le_const(other.upper)
        return False

    def make_le_const(self, value):
        """
        Sets the bounds of `self` so that it
        only contains values lower than or equal
        to `value`.
        Returns `True` iff the bound was updated.
        (Mutates `self`.)
        """
        if not self.has_upper or value < self.upper:
            self.has_upper = True
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
        if other.has_upper:
            return self.make_lt_const(other.upper)
        return False

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
        if other.has_lower:
            return self.make_ge_const(other.lower)
        return False

    def make_ge_const(self, value):
        """
        Sets the bounds of `self` so that it
        only contains values greater than or equal
        to `value`.
        Returns `True` iff the bound was updated.
        (Mutates `self`.)
        """
        if not self.has_lower or value > self.lower:
            self.has_lower = True
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
        if other.has_lower:
            return self.make_gt_const(other.lower)
        return False

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
        self.has_upper = True
        self.has_lower = True
        self.upper = intval
        self.lower = intval
        self.tvalue = r_uint(intval)
        self.tmask = r_uint(0)

    def is_constant_by_bounds(self):
        """ for internal use only! """
        return self.is_bounded() and (self.lower == self.upper)

    def is_constant_by_knownbits(self):
        """ for internal use only! """
        return self.tmask == 0

    def is_constant(self):
        """
        Returns `True` iff this abstract integer
        does contain only one (1) concrete integer.
        """
        return self.is_constant_by_bounds() or self.is_constant_by_knownbits()

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

    def is_bounded(self):
        """
        Returns `True` iff this abstract integer
        has both, a lower and an upper bound.
        """
        return self.has_lower and self.has_upper

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
        if self.has_upper:
            return self.upper < value
        return False

    def known_le_const(self, value):
        """
        Returns `True` iff each number contained
        in this abstract integer is lower than
        or equal to `value`.
        """
        if self.has_upper:
            return self.upper <= value
        return False

    def known_gt_const(self, value):
        """
        Returns `True` iff each number contained
        in this abstract integer is greater than
        `value`.
        """
        if self.has_lower:
            return self.lower > value
        return False

    def known_ge_const(self, value):
        """
        Returns `True` iff each number contained
        in this abstract integer is greater than
        equal to `value`.
        """
        if self.has_upper:
            return self.upper >= value
        return False

    def known_lt(self, other):
        """
        Returns `True` iff each number contained
        in this abstract integer is lower than
        each integer contained in `other`.
        """
        if other.has_lower:
            return self.known_lt_const(other.lower)
        return False

    def known_le(self, other):
        """
        Returns `True` iff each number contained
        in this abstract integer is lower than
        or equal to each integer contained in
        `other`.
        """
        if other.has_lower:
            return self.known_le_const(other.lower)
        return False

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
        #return self.has_lower and 0 <= self.lower
        return 0 <= self.get_minimum()

    def known_nonnegative_by_bounds(self):
        """ for internal use only! """
        # Returns `True` if this abstract integer
        # only contains numbers greater than or
        # equal to `0` (zero), IGNORING KNOWNBITS.
        if not self.has_lower:
            return False
        else:
            return 0 <= self.lower

    def get_minimum_by_knownbits(self):
        """ for internal use only! """
        return intmask(self.tvalue | msbonly(self.tmask))

    def get_maximum_by_knownbits(self):
        """ for internal use only! """
        unsigned_mask = self.tmask & ~(1<<(LONG_BIT-1))
        return intmask(self.tvalue | unsigned_mask)

    def get_minimum(self):
        """
        Returns the lowest integer that is
        contained in this abstract integer.
        """
        # Unnecessary to unmask, because by convention
        #   mask[i] => ~value[i]
        ret_knownbits = self.get_minimum_by_knownbits()
        ret_bounds = self.lower
        if self.has_lower:
            return max(ret_knownbits, ret_bounds)
        else:
            return ret_knownbits

    def get_maximum(self):
        """
        Returns the greatest integer that is
        contained in this abstract integer.
        """
        ret_knownbits = self.get_maximum_by_knownbits()
        ret_bounds = self.upper
        if self.has_upper:
            return min(ret_knownbits, ret_bounds)
        else:
            return ret_knownbits

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

        # we also assert agreement between knownbits and bounds,
        # e.g. that the set of possible ints is not empty.
        if self.has_lower:
            max_knownbits = self.get_maximum_by_knownbits()
            assert max_knownbits >= self.lower
        if self.has_upper:
            min_knownbits = self.get_minimum_by_knownbits()
            assert min_knownbits <= self.upper

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

    def add(self, offset):
        """
        Adds `offset` to this abstract int
        and returns the result.
        (Does not mutate `self`.)
        """
        return self.add_bound(ConstIntBound(offset))

    def mul(self, value):
        """
        Multiplies this abstract int with the
        given `value` and returns the result.
        (Does not mutate `self`.)
        """
        return self.mul_bound(ConstIntBound(value))

    def add_bound(self, other):
        """
        Adds the `other` abstract integer to
        `self` and returns the result.
        (Does not mutate `self`.)
        """

        res = self.clone()

        sum_values = self.tvalue + other.tvalue
        sum_masks = self.tmask + other.tmask
        all_carries = sum_values + sum_masks
        val_carries = all_carries ^ sum_values
        res.tmask = self.tmask | other.tmask | val_carries
        res.tvalue = unmask_zero(sum_values, res.tmask)

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
        """
        Subtracts the `other` abstract
        integer from `self` and returns the
        result.
        (Does not mutate `self`.)
        """
        res = self.add_bound(other.neg_bound())
        return res

    def mul_bound(self, other):
        """
        Multiplies the `other` abstract
        integer with `self` and returns the
        result.
        (Does not mutate `self`.)
        """
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
        """
        Divides this abstract integer by the
        `other` abstract integer and returns
        the result.
        (Does not mutate `self`.)
        """
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
            elif c_other >= 0:
                tvalue = self.tvalue << r_uint(c_other)
                tmask = self.tmask << r_uint(c_other)
            # else: bits are unknown because arguments invalid

        if self.is_bounded() and other.is_bounded() and \
           other.known_nonnegative_by_bounds() and \
           other.known_lt_const(LONG_BIT):
            try:
                vals = (ovfcheck(self.upper << other.upper),
                        ovfcheck(self.upper << other.lower),
                        ovfcheck(self.lower << other.upper),
                        ovfcheck(self.lower << other.lower))
                return IntLowerUpperBoundKnownbits(min4(vals), max4(vals),
                                                   tvalue, tmask)
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

        if self.is_bounded() and other.is_bounded() and \
           other.known_nonnegative_by_bounds() and \
           other.known_lt_const(LONG_BIT):
            vals = (self.upper >> other.upper,
                    self.upper >> other.lower,
                    self.lower >> other.upper,
                    self.lower >> other.lower)
            return IntLowerUpperBoundKnownbits(min4(vals), max4(vals),
                                               tvalue, tmask)
        else:
            return IntBoundKnownbits(tvalue, tmask)

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

        r = IntUnbounded()

        if self.known_nonnegative_by_bounds() and \
                other.known_nonnegative_by_bounds():
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
        """
        Performs bit-wise XOR of this
        abstract integer and the `other`,
        returning its result.
        (Does not mutate `self`.)
        """

        r = IntUnbounded()

        if self.known_nonnegative_by_bounds() and \
                other.known_nonnegative_by_bounds():
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
        """
        Performs bit-wise NOT on this
        abstract integer returning its
        result.
        (Does not mutate `self`.)
        """

        res = self.clone()

        res.has_upper = False
        if self.has_lower:
            res.upper = ~self.lower
            res.has_upper = True
        res.has_lower = False
        if self.has_upper:
            res.lower = ~self.upper
            res.has_lower = True

        res.tvalue = unmask_zero(~res.tvalue, res.tmask)

        return res

    def neg_bound(self):
        """
        Arithmetically negates this abstract
        integer and returns the result.
        (Does not mutate `self`.)
        """
        res = self.invert_bound()
        res = res.add(1)
        return res

    def contains(self, val):
        """
        Returns `True` iff this abstract
        integer contains the given `val`ue.
        """

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

        u_vself = unmask_zero(self.tvalue, self.tmask)
        u_value = unmask_zero(r_uint(val), self.tmask)
        if u_vself != u_value:
            return False

        return True

    def contains_bound(self, other):
        """
        Returns `True` iff this abstract
        integers contains each number that
        is contained in the `other` one.
        """

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
        """
        Returns an exact copy of this
        abstract integer.
        """
        res = IntBound(self.lower, self.upper,
                       self.has_lower, self.has_upper,
                       self.tvalue, self.tmask)
        return res

    def make_guards(self, box, guards, optimizer):
        """
        Generates guards from the information
        we have about the numbers this
        abstract integer contains.
        """
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
        """
        Returns `True` iff the properties
        of this abstract integer allow it to
        represent a conventional boolean
        value.
        """
        return (self.is_bounded() and self.known_nonnegative() and
                self.known_le_const(1))

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

    def int_and_backwards(self, other, result_int):
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
         1  ?   1   ?
         ?  ?   ?   ?   <- self
        result

        If the knownbits of self and result are inconsistent,
        the values of result are used (this must not happen
        in practice and will be caught by an assert in intersect())
        """

        tvalue = self.tvalue
        tmask = self.tmask
        tvalue &= ~other.tvalue & ~other.tmask
        tvalue |= r_uint(result_int) & other.tvalue
        tmask &= ~other.tvalue | other.tmask
        return IntBoundKnownbits(tvalue, tmask)

    def int_or_backwards(self, other, result_int):
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

        TODO: Open question: What to do on X?
        If the knownbits of self and result are inconsistent,
        the values of result are used (this must not happen
        in practice and will be caught by an assert in intersect())
        """
        pass


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
    b = IntBound(lower=lower,
                 upper=upper,
                 has_lower=True,
                 has_upper=True)
    """
    Constructs an abstract integer that is
    greater than or equal to `lower` and
    lower than or equal to `upper`, e.g.
    it is bound by `lower` and `upper`.
    """
    return b

def IntUpperBound(upper):
    b = IntBound(lower=0,
                 upper=upper,
                 has_lower=False,
                 has_upper=True)
    """
    Constructs an abstract integer that is
    lower than or equal to `upper`, e.g.
    it is bound by `upper`.
    """
    return b

def IntLowerBound(lower):
    b = IntBound(lower=lower,
                 upper=0,
                 has_lower=True,
                 has_upper=False)
    """
    Constructs an abstract integer that is
    greater than or equal to `lower`, e.g.
    it is bound by `lower`.
    """
    return b

def IntUnbounded():
    """
    Constructs an abstract integer that is
    completely unknown (e.g. it contains
    every integer).
    """
    b = IntBound()
    return b

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
    if not isinstance(value, int):
        # workaround for AddressAsInt / symbolic ints
        # by CF
        tvalue = 0
        tmask = -1
    b = IntBound(lower=value,
                 upper=value,
                 has_lower=True,
                 has_upper=True,
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
    b = IntBound(lower=0,
                 upper=0,
                 has_lower=False,
                 has_upper=False,
                 tvalue=value,
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
                 has_lower=True,
                 has_upper=True,
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

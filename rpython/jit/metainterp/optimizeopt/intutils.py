"""
This file contains an abstract domain IntBound for word-sized integers. This is
used to perform abstract interpretation on traces, specifically the integer
operations on them.

The abstract domain tracks a (signed) upper and lower bound (both ends
inclusive) for every integer variable in the trace. It also tracks which bits
of a range are known 0 or known 1 (the remaining bits are unknown. The ranges
and the known bits feed back into each other, ie we can improve the range if
some upper bits have known values, and we can learn some known bits from the
range too. Every instance of IntBound represents a set of concrete integers.

We do the analysis at the same time as optimization. We initialize all integer
variables to have an unknown range, with no known bits. Then we proceed along
the trace and improve the ranges. We can shrink ranges if we see integer
comparisons followed by guards. We can learn some bits of an integer if there
are bit-operations such as `and` (masking out some bits), followed by a guard.

For every operation in the trace we use a "transfer function" that computes an
IntBound instance for the result of that operation, given the IntBounds of the
arguments. Those functions are called `..._bound`, eg `add_bound`, `and_bound`,
`neg_bound`, etc. Applying the transfer functions while we encounter them along
the trace is forwards reasoning.

We can also reason backwards (but we only do that in a limited way). Here's an
example:

i1 = int_add(i0, 1)
i2 = int_lt(i1, 100)
guard_true(i2)

At the last guard we learn that i1 < 100 must be true, and from that we can
conclude that i0 < 99 in the rest of the trace (this is not quite true due to
possible overflow of the int_add).

More generally, when we shrink (ie make more precise) an IntBound instance due
to a guard, we can often conclude something about earlier variables in the
trace. To reason backwards we look at the operation that created a variable and
then compute the implications.

The reason for having both a range and known bits are that each of them is good
for different situations. Range knownledge is useful for comparisons and
"linear" operations like additions, subtractions, multiplications, etc.
Knowledge about certain bits is good for bit twiddling code, bitfields, stuff
like that.
"""

import sys
from rpython.rlib.rarithmetic import ovfcheck, LONG_BIT, maxint, is_valid_int, r_uint, intmask
from rpython.rlib.objectmodel import we_are_translated, always_inline
from rpython.rtyper.lltypesystem import lltype
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.jit.metainterp.resoperation import rop, ResOperation
from rpython.jit.metainterp.optimize import InvalidLoop
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


class IntBound(AbstractInfo):
    """
    Abstract domain representation of an integer,
    approximating via integer bounds and known-bits
    tri-state numbers.
    """
    _attrs_ = ('upper', 'lower', 'tvalue', 'tmask')

    def __init__(self, lower=MININT, upper=MAXINT,
                 tvalue=TNUM_ONLY_VALUE_DEFAULT,
                 tmask=TNUM_ONLY_MASK_DEFAULT,
                 do_shrinking=True):
        """
        Instantiates an abstract representation of integer.
        The default parameters set this abstract int to
        contain all integers.

        It is recommended to use the indirect constructors
        below instead of this one.
        """

        self.lower = lower
        self.upper = upper

        # known-bit analysis using tristate/knownbits numbers:
        # every bit can be either 0, 1, or unknown (?).
        # the encoding of these three states is:
        # value       0 1 ?
        # tvalue bit  0 1 0
        # tmask bit   0 0 1
        # the combination tvalue=tmask=1 is forbidden
        assert is_valid_tnum(tvalue, tmask)
        self.tvalue = tvalue
        self.tmask = tmask         # bit=1 means unknown

        # check for unexpected overflows:
        if not we_are_translated():
            assert type(upper) is not long or is_valid_int(upper)
            assert type(lower) is not long or is_valid_int(lower)

        if do_shrinking:
            self.shrink()
            assert self._debug_check()

    @staticmethod
    def from_constant(value):
        """
        Constructs an abstract integer that represents a constant (a completely
        known integer).
        """
        # this one does NOT require a r_uint for `value`.
        assert not isinstance(value, r_uint)
        tvalue = value
        tmask = 0
        bvalue = value
        do_shrinking = False
        if not isinstance(value, int):
            # workaround for AddressAsInt / symbolic ints
            # by CF
            tvalue = 0
            tmask = -1
            bvalue = 0
            do_shrinking = True
        b = IntBound(lower=bvalue,
                     upper=bvalue,
                     tvalue=r_uint(tvalue),
                     tmask=r_uint(tmask), do_shrinking=do_shrinking)
        return b

    @staticmethod
    def unbounded():
        """
        Constructs an abstract integer that is completely unknown (e.g. it
        contains every integer).
        """
        return IntBound(do_shrinking=False)

    @staticmethod
    def nonnegative():
        """
        Construct a non-negative abstract integer.
        """
        return IntBound(lower=0)

    @staticmethod
    def from_knownbits(tvalue, tmask, do_unmask=False):
        """
        Constructs an abstract integer where the bits determined by `tvalue`
        and `tmask` are (un-)known. tvalue and tmask must be r_uints.
        """
        assert isinstance(tvalue, r_uint) and isinstance(tmask, r_uint)
        if do_unmask:
            tvalue = unmask_zero(tvalue, tmask)
        return IntBound(tvalue=tvalue,
                        tmask=tmask)

    # ____________________________________________________________
    # a bunch of slightly artificial methods that are needed to make some of
    # the Z3 proofs in test_z3intbound possible, they are overridden there

    @staticmethod
    @always_inline
    def new(lower, upper, tvalue, tmask):
        """ helper factory to construct a new IntBound. overridden in
        test_z3intbound """
        return IntBound(lower, upper, tvalue, tmask)

    intmask = staticmethod(intmask)
    r_uint = staticmethod(r_uint)

    @staticmethod
    @always_inline
    def _add_check_overflow(a, b, value_if_overflow):
        """ returns a + b, or value_if_overflow if that (signed) addition would
        overflow """
        try:
            return ovfcheck(a + b)
        except OverflowError:
            return value_if_overflow

    @staticmethod
    @always_inline
    def _sub_check_overflow(a, b, value_if_overflow):
        """ returns a - b, or value_if_overflow if that (signed) subtraction would
        overflow """
        try:
            return ovfcheck(a - b)
        except OverflowError:
            return value_if_overflow

    @staticmethod
    @always_inline
    def _urshift(a, b):
        return r_uint(a) >> r_uint(b)

    # ____________________________________________________________

    @staticmethod
    def _to_dec_or_hex_str_heuristics(num):
        # a few formatting heuristics
        if -1000 <= num <= 1000:
            return str(num)
        if num == MININT:
            return "MININT"
        if num == MAXINT:
            return "MAXINT"
        if num >= 0:
            diff = MAXINT - num
            if diff < 1000:
                return "MAXINT - %s" % diff
        else:
            diff = -(MININT - num) # can't overflow because num < 0
            if diff < 1000:
                return "MININT + %s" % diff
        uintnum = r_uint(num)
        if uintnum & (uintnum - 1) == 0:
            # power of two, use hex
            return hex(num)
        # format number as decimal if fewer than 6 significant
        # digits, otherwise use hex
        curr = num
        exp10 = 0
        while curr % 10 == 0:
            curr //= 10
            exp10 += 1
        s = str(num)
        if len(s) - exp10 >= 6:
            return hex(num)
        return s

    def _are_knownbits_implied(self):
        """ return True if the knownbits of self are a direct consequence of
        the range of self (and thus carry no extra information) """
        tvalue, tmask = self._tnum_implied_by_bounds()
        return self.tmask == tmask and self.tvalue == tvalue

    def _are_bounds_implied(self):
        """ return True if the bounds of self are a direct consequence of the
        knownbits of self (and thus carry no extra information) """
        lower = self._get_minimum_signed_by_knownbits()
        upper = self._get_maximum_signed_by_knownbits()
        return self.lower == lower and self.upper == upper

    def __repr__(self):
        if self.is_unbounded():
            return "IntBound.unbounded()"
        if self.lower == 0 and self.upper == MAXINT and self._are_knownbits_implied():
            return "IntBound.nonnegative()"
        if self.is_constant():
            return "IntBound.from_constant(%s)" % self._to_dec_or_hex_str_heuristics(self.get_constant_int())
        s_bounds = "%s, %s" % (self._to_dec_or_hex_str_heuristics(self.lower),
                               self._to_dec_or_hex_str_heuristics(self.upper))

        if self._are_knownbits_implied():
            return "IntBound(%s)" % s_bounds

        s_tnum = "r_uint(%s), r_uint(%s)" % (bin(intmask(self.tvalue)), bin(intmask(self.tmask)))
        if self._are_bounds_implied():
            return "IntBound.from_knownbits(%s)" % s_tnum
        return "IntBound(%s, %s)" % (s_bounds, s_tnum)

    def __str__(self):
        if self.is_constant():
            return '(%s)' % self._to_dec_or_hex_str_heuristics(self.get_constant_int())
        if self.lower == 0 and self.upper == 1:
            return '(bool)'
        if self.lower == MININT:
            lower = ''
        else:
            lower = '%s <= ' % self._to_dec_or_hex_str_heuristics(self.lower)
        if self.upper == MAXINT:
            upper = ''
        else:
            upper = ' <= %s' % self._to_dec_or_hex_str_heuristics(self.upper)
        s = self.knownbits_string()
        if "0" not in s and "1" not in s:
            s = '?'
        else:
            # replace the longest sequence of same characters by ...
            prev_char = s[0]
            count = 0
            max_length = 0
            max_char = '\x00'
            start_pos = 0
            max_pos = -1
            for pos, char in enumerate(s):
                if char == prev_char:
                    count += 1
                else:
                    if count > max_length:
                        max_length = count
                        max_char = prev_char
                        max_pos = start_pos
                    prev_char = char
                    count = 1
                    start_pos = pos
            if count > max_length:
                max_length = count
                max_char = prev_char
                max_pos = start_pos
            if max_length > 5:
                assert max_pos >= 0
                s = s[:max_pos] + max_char + "..." + max_char + s[max_pos + max_length:]
            s = '0b' + s
        return '(%s%s%s)' % (lower, s, upper)

    def set_tvalue_tmask(self, tvalue, tmask):
        changed = self.tvalue != tvalue or self.tmask != tmask
        if changed:
            self.tvalue = tvalue
            self.tmask = tmask
            self.shrink()
        return changed

    def make_le(self, other):
        """
        Sets the bounds of `self` so that it only contains values lower than or
        equal to the values contained in `other`. Returns `True` iff the bound
        was updated. Will raise InvalidLoop if the resulting interval is empty.
        Mutates `self`.
        """
        return self.make_le_const(other.upper)

    def make_le_const(self, value):
        """
        Sets the bounds of `self` so that it only contains values lower than or
        equal to `value`. Returns `True` iff the bound was updated. Will raise
        InvalidLoop if the resulting interval is empty.
        Mutates `self`.
        """
        if value < self.upper:
            if value < self.lower:
                raise InvalidLoop
            self.upper = value
            self.shrink()
            return True
        return False

    def make_lt(self, other):
        """
        Sets the bounds of `self` so that it only contains values lower than
        the values contained in `other`. Returns `True` iff the bound was
        updated. Will raise InvalidLoop if the resulting interval is empty.
        (Mutates `self`.)
        """
        return self.make_lt_const(other.upper)

    def make_lt_const(self, value):
        """
        Sets the bounds of `self` so that it only contains values lower than
        `value`. Returns `True` iff the bound was updated. Will raise
        InvalidLoop if the resulting interval is empty. (Mutates `self`.)
        """
        if value == MININT:
            raise InvalidLoop("intbound can't be made smaller than MININT")
        return self.make_le_const(value - 1)

    def make_ge(self, other):
        """
        Sets the bounds of `self` so that it only contains values greater than
        or equal to the values contained in `other`. Returns `True` iff the
        bound was updated. Will raise InvalidLoop if the resulting interval is
        empty. (Mutates `self`.)
        """
        return self.make_ge_const(other.lower)

    def make_ge_const(self, value):
        """
        Sets the bounds of `self` so that it only contains values greater than
        or equal to `value`. Returns `True` iff the bound was updated. Will
        raise InvalidLoop if the resulting interval is empty. (Mutates `self`.)
        """
        if value > self.lower:
            if value > self.upper:
                raise InvalidLoop
            self.lower = value
            self.shrink()
            return True
        return False

    def make_gt(self, other):
        """
        Sets the bounds of `self` so that it only contains values greater than
        the values contained in `other`. Returns `True` iff the bound was
        updated. Will raise InvalidLoop if the resulting interval is empty.
        (Mutates `self`.)
        """
        return self.make_gt_const(other.lower)

    def make_gt_const(self, value):
        """
        Sets the bounds of `self` so that it only contains values greater than
        `value`. Returns `True` iff the bound was updated. Will raise
        InvalidLoop if the resulting interval is empty. (Mutates `self`.)
        """
        if value == MAXINT:
            raise InvalidLoop
        return self.make_ge_const(value + 1)

    def make_eq_const(self, intval):
        """
        Sets the properties of this abstract integer
        so that it is constant and equals `intval`.
        (Mutates `self`.)
        """
        if not self.contains(intval):
            raise InvalidLoop("constant int is outside of interval")
        self.upper = intval
        self.lower = intval
        self.tvalue = r_uint(intval)
        self.tmask = r_uint(0)

    def make_ne_const(self, intval):
        if self.lower < intval == self.upper:
            self.upper -= 1
            self.shrink()
            return True
        if self.lower == intval < self.upper:
            self.lower += 1
            self.shrink()
            return True
        return False

    def is_constant(self):
        """
        Returns `True` iff this abstract integer
        does contain only one concrete integer.
        """
        # both the bounds and the tnum encode the concrete integer
        res = self.lower == self.upper
        assert res == (self.tmask == r_uint(0))
        if res:
            assert self.lower == intmask(self.tvalue)
        return res

    def get_constant_int(self):
        """
        Returns the only integer contained in this abstract integer. Caller
        needs to check that `.is_constant()` returns True, before calling.
        """
        assert self.is_constant()
        return self.lower

    def known_eq_const(self, value):
        """
        Returns `True` iff this abstract integer contains only one (1) integer
        that does equal `value`.
        """
        if not self.is_constant():
            return False
        else:
            return self.lower == value

    def known_lt_const(self, value):
        """
        Returns `True` iff each number contained in this abstract integer is
        lower than `value`.
        """
        return self.upper < value

    def known_le_const(self, value):
        """
        Returns `True` iff each number contained in this abstract integer is
        lower than or equal to `value`.
        """
        return self.upper <= value

    def known_gt_const(self, value):
        """
        Returns `True` iff each number contained in this abstract integer is
        greater than `value`.
        """
        return self.lower > value

    def known_ge_const(self, value):
        """
        Returns `True` iff each number contained in this abstract integer is
        greater than equal to `value`.
        """
        return self.lower >= value

    def known_lt(self, other):
        """
        Returns `True` iff each number contained in this abstract integer is
        lower than each integer contained in `other`.
        """
        return self.known_lt_const(other.lower)

    def known_le(self, other):
        """
        Returns `True` iff each number contained in this abstract integer is
        lower than or equal to each integer contained in `other`.
        """
        return self.known_le_const(other.lower)

    def known_gt(self, other):
        """
        Returns `True` iff each number contained in this abstract integer is
        greater than each integer contained in `other`.
        """
        return other.known_lt(self)

    def known_ge(self, other):
        """
        Returns `True` iff each number contained in this abstract integer is
        greater than or equal to each integer contained in `other`.
        """
        return other.known_le(self)

    def known_ne(self, other):
        """ return True if the sets of numbers self and other must be disjoint.
        """
        # easy cases part 1: ranges don't overlap
        if self.known_lt(other):
            return True
        if self.known_gt(other):
            return True
        # easy case part 2: check whether the knownbits contradict
        both_known = self.tmask | other.tmask
        if unmask_zero(self.tvalue, both_known) != unmask_zero(other.tvalue, both_known):
            return True
        # for more complicated interactions between ranges and knownbits use
        # the logic in intersect
        newself = self.clone()
        try:
            newself.intersect(other)
        except InvalidLoop:
            return True
        return False

    def known_nonnegative(self):
        """
        Returns `True` if this abstract integer only contains numbers greater
        than or equal to `0` (zero).
        """
        return 0 <= self.lower

    def make_unsigned_le(self, other):
        if other.known_nonnegative():
            return self.intersect_const(0, other.upper)
        return False

    def make_unsigned_lt(self, other):
        if other.known_nonnegative():
            assert other.upper >= 0
            if other.upper == 0:
                raise InvalidLoop
            return self.intersect_const(0, other.upper - 1)
        return False

    def make_unsigned_ge(self, other):
        if other.upper < 0:
            changed = self.make_lt_const(0)
            return self.make_ge(other) or changed
        if self.known_nonnegative() and other.known_nonnegative():
            return self.make_ge(other)
        return False

    def make_unsigned_gt(self, other):
        if other.upper < 0:
            changed = self.make_lt_const(0)
            return self.make_gt(other) or changed
        if self.known_nonnegative() and other.known_nonnegative():
            return self.make_gt(other)
        return False

    def _known_same_sign(self, other):
        # return True if self and other are both either known non-negative or
        # both known negative
        if self.known_nonnegative() and other.known_nonnegative():
            return True
        return self.known_lt_const(0) and other.known_lt_const(0)

    def known_unsigned_lt(self, other):
        """
        Returns `True` iff each unsigned integer contained in this abstract
        integer is lower than each unsigned integer contained in `other`.
        """
        # if they have the same sign, we can reason with signed comparison
        # see test_uint_cmp_equivalent_int_cmp_if_same_sign
        if self._known_same_sign(other) and self.known_lt(other):
            return True
        other_min_unsigned_by_knownbits = other.get_minimum_unsigned_by_knownbits()
        self_max_unsigned_by_knownbits = self.get_maximum_unsigned_by_knownbits()
        return self_max_unsigned_by_knownbits < other_min_unsigned_by_knownbits

    def known_unsigned_le(self, other):
        """
        Returns `True` iff each unsigned integer contained in this abstract
        integer is lower or equal than each unsigned integer contained in
        `other`. """
        # if they have the same sign, we can reason with signed comparison
        if self._known_same_sign(other) and self.known_le(other):
            return True
        other_min_unsigned_by_knownbits = other.get_minimum_unsigned_by_knownbits()
        self_max_unsigned_by_knownbits = self.get_maximum_unsigned_by_knownbits()
        return self_max_unsigned_by_knownbits <= other_min_unsigned_by_knownbits

    def known_unsigned_gt(self, other):
        """
        Returns `True` iff each unsigned integer contained in this abstract
        integer is greater than each unsigned integer contained in `other`.
        """
        return other.known_unsigned_lt(self)

    def known_unsigned_ge(self, other):
        """
        Returns `True` iff each unsigned integer contained in this abstract
        integer is greater or equal than each unsigned integer contained in
        `other`.
        """
        return other.known_unsigned_le(self)

    def get_minimum_unsigned_by_knownbits(self):
        """
        Returns the minimum unsigned number, but only using the knownbits as
        information."""
        return unmask_zero(self.tvalue, self.tmask)

    def get_maximum_unsigned_by_knownbits(self):
        """
        returns the maximum unsigned number, but only using the knownbits as
        information."""
        return unmask_one(self.tvalue, self.tmask)

    def _get_minimum_signed_by_knownbits(self):
        """ for internal use only!
        returns the minimum signed number, but only using the knownbits as
        information."""
        return self.intmask(self.tvalue | msbonly(self.tmask))

    def _get_maximum_signed_by_knownbits(self):
        """ for internal use only!
        returns the maximum signed number, but only using the knownbits as
        information."""
        unsigned_mask = self.tmask & ~msbonly(self.tmask)
        return self.intmask(self.tvalue | unsigned_mask)

    def _get_minimum_signed_by_knownbits_atleast(self, threshold=MININT):
        """ for internal use only!
        return the smallest number permitted by the known bits that is above
        (or equal) threshold. will raise InvalidLoop if no such number exists.
        """
        if self._get_maximum_signed_by_knownbits() < threshold:
            raise InvalidLoop("threshold and knownbits don't overlap")
        min_by_knownbits = self._get_minimum_signed_by_knownbits()
        if min_by_knownbits > self.upper:
            raise InvalidLoop("range and knownbits don't overlap")
        if min_by_knownbits >= threshold:
            return min_by_knownbits
        # see "Sharpening Constraint Programming
        #      approaches for Bit-Vector Theory"
        u_min_threshold = r_uint(threshold)
        # create our working value, the to-be minimum
        working_min, cl2set, set2cl = self._helper_min_max_prepare(u_min_threshold)
        if working_min == u_min_threshold:
            return threshold
        elif cl2set > set2cl:
            return self._helper_min_case1(working_min, cl2set)
        else:
            return self._helper_min_case2(working_min, set2cl)

    @always_inline
    def _helper_min_max_prepare(self, u_threshold):
        working_value = u_threshold # start at given threshold
        working_value &= unmask_one(self.tvalue, self.tmask) # clear known 0s
        working_value |= self.tvalue # set known 1s
        # inspect changed bits
        cl2set = ~u_threshold & working_value
        set2cl = u_threshold & ~working_value
        return working_value, cl2set, set2cl

    @always_inline
    def _helper_min_case1(self, working_min, cl2set):
        # we have set the correct bit already
        clear_mask = leading_zeros_mask(self._urshift(cl2set, 1))
        working_min &= clear_mask | ~self.tmask
        return self.intmask(working_min)

    @always_inline
    def _helper_min_case2(self, working_min, set2cl):
        # flip the sign bit to handle -1 -> 0 overflow
        working_min = flip_msb(working_min)
        # we have to find the proper bit to set...
        possible_bits = ~working_min \
                        & self.tmask \
                        & leading_zeros_mask(set2cl)
        bit_to_set = lowest_set_bit_only(possible_bits)
        working_min |= bit_to_set
        # and clear all lower than that
        clear_mask = leading_zeros_mask(bit_to_set) \
                     | bit_to_set | ~self.tmask
        working_min &= clear_mask
        return self.intmask(flip_msb(working_min))

    def _get_maximum_signed_by_knownbits_atmost(self, threshold=MAXINT):
        """ for internal use only!
        return the largest number permitted by the known bits that is below or
        equal to threshold. will raise InvalidLoop if no such number exists.
        """
        if self._get_minimum_signed_by_knownbits() > threshold:
            raise InvalidLoop("threshold and knownbits don't overlap")
        max_by_knownbits = self._get_maximum_signed_by_knownbits()
        if max_by_knownbits < self.lower:
            raise InvalidLoop("range and knownbits don't overlap")
        if max_by_knownbits <= threshold:
            return max_by_knownbits
        # see "Sharpening Constraint Programming
        #      approaches for Bit-Vector Theory"
        u_max_threshold = r_uint(threshold)
        # now create our working value, the to-be maximum
        working_max, cl2set, set2cl = self._helper_min_max_prepare(u_max_threshold)
        if working_max == u_max_threshold:
            return threshold
        elif cl2set < set2cl:
            # we have cleared the right bit already
            result = self._helper_max_case1(working_max, set2cl)
        else:
            result = self._helper_max_case2(working_max, cl2set)
        assert result <= threshold
        return result

    def _helper_max_case1(self, working_max, set2cl):
        # we have cleared the right bit already
        set_mask = next_pow2_m1(self._urshift(set2cl, 1)) & self.tmask
        working_max |= set_mask
        return self.intmask(working_max)

    def _helper_max_case2(self, working_max, cl2set):
        # flip the sign bit to handle 1 -> 0 overflow
        working_max = flip_msb(working_max)
        # find the right bit to clear
        possible_bits = working_max \
                        & self.tmask \
                        & leading_zeros_mask(cl2set)
        bit_to_clear = lowest_set_bit_only(possible_bits)
        working_max &= ~bit_to_clear
        # and set all lower than that
        set_mask = next_pow2_m1(self._urshift(bit_to_clear, 1)) & self.tmask
        working_max |= set_mask
        return self.intmask(flip_msb(working_max))


    def _get_minimum_signed(self):
        """ for tests only """
        ret_b = self.lower
        result = self._get_minimum_signed_by_knownbits_atleast(ret_b)
        assert isinstance(result, int)
        return result

    def _get_maximum_signed(self):
        """ for tests only """
        ret_b = self.upper
        result = self._get_maximum_signed_by_knownbits_atmost(ret_b)
        assert isinstance(result, int)
        return result

    def intersect(self, other):
        """
        Mutates `self` so that it contains integers that are contained in
        `self` and `other`, and only those. Basically intersection of sets.
        Throws InvalidLoop if `self` and `other` "disagree", meaning the result
        would not contain any integers.
        """
        if self.known_gt(other) or self.known_lt(other):
            # they don't overlap, which makes the loop invalid
            # this never happens in regular linear traces, but it can happen in
            # combination with unrolling/loop peeling
            raise InvalidLoop("two integer ranges don't overlap")

        r = self.intersect_const(other.lower, other.upper, do_shrinking=False)

        tvalue, tmask, valid = self._tnum_intersect(other.tvalue, other.tmask)
        if not valid:
            raise InvalidLoop("knownbits contradict each other")
        # calculate intersect value and mask
        if self.tmask != tmask:
            # this can also raise InvalidLoop, if the ranges and knownbits
            # contradict in more complicated ways
            r = self.set_tvalue_tmask(tvalue, tmask) # this shrinks
            assert r
        elif r:
            # we didn't shrink yet
            self.shrink()
            assert self._debug_check()
        return r

    @always_inline
    def _tnum_intersect(self, other_tvalue, other_tmask):
        union_val = self.tvalue | other_tvalue
        either_known = self.tmask & other_tmask
        both_known = self.tmask | other_tmask
        unmasked_self = unmask_zero(self.tvalue, both_known)
        unmasked_other = unmask_zero(other_tvalue, both_known)
        tvalue = unmask_zero(union_val, either_known)
        valid = unmasked_self == unmasked_other
        return tvalue, either_known, valid

    def intersect_const(self, lower, upper, do_shrinking=True):
        """
        Mutates `self` so that it contains integers that are contained in
        `self` and the range [`lower`, `upper`], and only those. Basically
        intersection of sets.
        """
        changed = False
        if lower > self.lower:
            if lower > self.upper:
                raise InvalidLoop
            self.lower = lower
            changed = True
        if upper < self.upper:
            if upper < self.lower:
                raise InvalidLoop
            self.upper = upper
            changed = True
        if changed and do_shrinking:
            self.shrink()
        return changed

    def add(self, value):
        return self.add_bound(self.from_constant(value))

    def add_bound(self, other):
        """
        Adds the `other` abstract integer to `self` and returns the result.
        Must be correct in the presence of possible overflows.
        (Does not mutate `self`.)
        """

        tvalue, tmask = self._tnum_add(other)

        # the lower and upper logic is proven in test_prove_add_bounds_logic
        try:
            lower = ovfcheck(self.lower + other.lower)
        except OverflowError:
            return IntBound.from_knownbits(tvalue, tmask)
        try:
            upper = ovfcheck(self.upper + other.upper)
        except OverflowError:
            return IntBound.from_knownbits(tvalue, tmask)
        return IntBound(lower, upper, tvalue, tmask)

    @always_inline
    def _tnum_add(self, other):
        sum_values = self.tvalue + other.tvalue
        sum_masks = self.tmask + other.tmask
        all_carries = sum_values + sum_masks
        val_carries = all_carries ^ sum_values
        tmask = self.tmask | other.tmask | val_carries
        tvalue = unmask_zero(sum_values, tmask)
        return tvalue, tmask

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
        tvalue, tmask = self._tnum_add(other)

        # returning add_bound is always correct, but let's improve the range
        lower = self._add_check_overflow(self.lower, other.lower, MININT)
        upper = self._add_check_overflow(self.upper, other.upper, MAXINT)
        return self.new(lower, upper, tvalue, tmask)

    def sub_bound(self, other):
        """
        Subtracts the `other` abstract integer from `self` and returns the
        result. (Does not mutate `self`.)
        """
        tvalue, tmask = self._tnum_sub(other)
        # the lower and upper logic is proven in test_prove_sub_bound_logic
        try:
            lower = ovfcheck(self.lower - other.upper)
        except OverflowError:
            return IntBound.from_knownbits(tvalue, tmask)
        try:
            upper = ovfcheck(self.upper - other.lower)
        except OverflowError:
            return IntBound.from_knownbits(tvalue, tmask)
        return IntBound(lower, upper, tvalue, tmask)

    def _tnum_sub(self, other):
        diff_values = self.tvalue - other.tvalue
        val_borrows = (diff_values + self.tmask) ^ (diff_values - other.tmask)
        tmask = self.tmask | other.tmask | val_borrows
        tvalue = unmask_zero(diff_values, tmask)
        return tvalue, tmask

    def sub_bound_cannot_overflow(self, other):
        try:
            ovfcheck(self.lower - other.upper)
            ovfcheck(self.upper - other.lower)
        except OverflowError:
            return False
        return True

    def sub_bound_no_overflow(self, other):
        """ return the bound that self - other must have, if no overflow occured,
        eg after an int_sub_ovf(...), guard_no_overflow() """
        tvalue, tmask = self._tnum_sub(other)
        # returning sub_bound is always correct, but let's improve the range
        lower = self._sub_check_overflow(self.lower, other.upper, MININT)
        upper = self._sub_check_overflow(self.upper, other.lower, MAXINT)
        return self.new(lower, upper, tvalue, tmask)

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
            return IntBound.unbounded()
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
        # we need to make sure that the 0 is not in the interval because
        # otherwise [-4, 4] / [-4, 4] would return [-1, 1], which is nonsense
        # see test_knownbits_div_bug. the first part of the check is not
        # enough, because 0 could be excluded by the known bits
        if not other.contains(0) and not (other.lower < 0 < other.upper):
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
        return IntBound.unbounded()

    def mod_bound(self, other):
        """
        Calculates the mod of this abstract
        integer by the `other` abstract
        integer and returns the result.
        (Does not mutate `self`.)
        """
        r = IntBound.unbounded()
        if other.is_constant() and other.get_constant_int() == 0:
            return IntBound.unbounded()
        # with Python's modulo:  0 <= (x % pos) < pos
        #                        neg < (x % neg) <= 0
        # see test_prove_mod_bound_logic
        if other.upper > 0:
            upper = other.upper - 1
        else:
            upper = 0
        if other.lower < 0:
            lower = other.lower + 1
        else:
            lower = 0
        return IntBound(lower, upper)

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
                tvalue, tmask = self._tnum_lshift(c_other)
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

        return IntBound.from_knownbits(tvalue, tmask)

    @always_inline
    def _tnum_lshift(self, c_other):
        # use signed integer sign extension logic
        tvalue = self.tvalue << c_other
        tmask = self.tmask << c_other
        return tvalue, tmask

    def rshift_bound(self, other):
        """
        Shifts this abstract integer `other` bits to the right, where `other`
        is another abstract integer, and extends its sign. This is the
        arithmetic shift on signed integers, ie the shifted in values are 0/1,
        depending on the sign.
        (Does not mutate `self`.)
        """

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
                tvalue, tmask = self._tnum_rshift(c_other)
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

    @always_inline
    def _tnum_rshift(self, c_other):
        # use signed integer sign extension logic
        tvalue = self.r_uint(self.intmask(self.tvalue) >> c_other)
        tmask = self.r_uint(self.intmask(self.tmask) >> c_other)
        return tvalue, tmask

    def lshift_bound_cannot_overflow(self, other):
        """ returns True if self << other can never overflow """
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
        Shifts this abstract integer `other` bits to the right, where `other`
        is another abstract integer, *without* extending its sign. (Does not
        mutate `self`.)
        """

        # this seems to always be the signed variant..?
        tvalue, tmask = TNUM_UNKNOWN
        if other.is_constant():
            c_other = other.get_constant_int()
            if c_other >= LONG_BIT:
                # no sign to extend, we get constant 0
                tvalue, tmask = TNUM_KNOWN_ZERO
            elif c_other >= 0:
                tvalue, tmask = self._tnum_urshift(c_other)
            # else: bits are unknown because arguments invalid

        # we don't do bounds on unsigned
        return IntBound.from_knownbits(tvalue, tmask)

    @always_inline
    def _tnum_urshift(self, c_other):
        tvalue = self._urshift(self.tvalue, c_other)
        tmask = self._urshift(self.tmask, c_other)
        return tvalue, tmask

    def and_bound(self, other):
        """
        Performs bit-wise AND of this abstract integer and the `other`,
        returning its result. (Does not mutate `self`.)
        """

        pos1 = self.known_nonnegative()
        pos2 = other.known_nonnegative()
        # the next three if-conditions are proven by test_prove_and_bound_logic
        lower = MININT
        upper = MAXINT
        if pos1 or pos2:
            lower = 0
        if pos1:
            upper = self.upper
        if pos2:
            upper = min(upper, other.upper)

        res_tvalue, res_tmask = self._tnum_and(other)
        return IntBound(lower, upper, res_tvalue, res_tmask)

    @always_inline
    def _tnum_and(self, other):
        self_pmask = self.tvalue | self.tmask
        other_pmask = other.tvalue | other.tmask
        and_vals = self.tvalue & other.tvalue
        return and_vals, self_pmask & other_pmask & ~and_vals

    def or_bound(self, other):
        """
        Performs bit-wise OR of this abstract integer and the `other`,
        returning its result. (Does not mutate `self`.)
        """

        tvalue, tmask = self._tnum_or(other)
        return self.from_knownbits(tvalue, tmask)

    @always_inline
    def _tnum_or(self, other):
        union_vals = self.tvalue | other.tvalue
        union_masks = self.tmask | other.tmask
        return union_vals, union_masks & ~union_vals

    def xor_bound(self, other):
        """
        Performs bit-wise XOR of this abstract integer and the `other`,
        returning its result.
        (Does not mutate `self`.)
        """
        tvalue, tmask = self._tnum_xor(other)
        return self.from_knownbits(tvalue, tmask)

    @always_inline
    def _tnum_xor(self, other):
        xor_vals = self.tvalue ^ other.tvalue
        union_masks = self.tmask | other.tmask
        return unmask_zero(xor_vals, union_masks), union_masks

    def neg_bound(self):
        """
        Arithmetically negates this abstract integer and returns the result.
        (Does not mutate `self`.)
        """
        res = self.invert_bound()
        res = res.add(1)
        return res

    def invert_bound(self):
        """
        Performs bit-wise NOT on this abstract integer returning its result.
        (Does not mutate `self`.)
        """
        upper = ~self.lower
        lower = ~self.upper
        tvalue = unmask_zero(~self.tvalue, self.tmask)
        tmask = self.tmask
        return self.new(lower, upper, tvalue, tmask)

    def contains(self, value):
        """
        Returns `True` iff this abstract integer contains the given `value`.
        """

        assert not isinstance(value, IntBound)

        if not we_are_translated():
            assert not isinstance(value, long)
        if not isinstance(value, int):
            if (self.lower == MININT and self.upper == MAXINT):
                return True # workaround for address as int
        if value < self.lower:
            return False
        if value > self.upper:
            return False

        u_vself = unmask_zero(self.tvalue, self.tmask)
        u_value = unmask_zero(r_uint(value), self.tmask)
        if u_vself != u_value:
            return False

        return True

    def is_within_range(self, lower, upper):
        """
        Check if all the numbers contained in this instance have are between
        lower and upper.
        """
        return lower <= self.lower and self.upper <= upper

    def clone(self):
        """
        Returns a copy of this abstract integer.
        """
        res = IntBound(self.lower, self.upper,
                       self.tvalue, self.tmask)
        return res

    def make_guards(self, box, guards, optimizer):
        """
        Generates guards from the information we have about the numbers this
        abstract integer contains.
        """
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
        if not self._are_knownbits_implied():
            op = ResOperation(rop.INT_AND, [box, ConstInt(intmask(~self.tmask))])
            guards.append(op)
            op = ResOperation(rop.GUARD_VALUE, [op, ConstInt(intmask(self.tvalue))])
            guards.append(op)

    def is_bool(self):
        """
        Returns `True` iff self is exactly the set {0, 1}
        """
        return (self.known_nonnegative() and self.known_le_const(1))

    def is_unbounded(self):
        return (self.lower == MININT and self.upper == MAXINT and
                self.tvalue == r_uint(0) and self.tmask == r_uint(-1))


    def make_bool(self):
        """
        Mutates this abstract integer so that it does represent a conventional
        boolean value.
        (Mutates `self`.)
        """
        self.intersect_const(0, 1)

    def getconst(self):
        """
        Returns ConstInt with the only integer contained in this abstract
        integer. Caller needs to check that `.is_constant()` returns True,
        before calling.
        """
        return ConstInt(self.get_constant_int())

    def getnullness(self):
        """
        Returns information about whether this this abstract integer is known
        to be zero or not to be zero.
        """
        if self.known_gt_const(0) or \
           self.known_lt_const(0) or \
           self.tvalue != 0:
            return INFO_NONNULL
        if self.is_constant() and self.get_constant_int() == 0:
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
        self.shrink()


    def and_bound_backwards(self, result):
        """
        result == int_and(self, other)
        We want to learn some bits about other, using the information from self
        and result_int.

        regular &:
                  other
         &  0   1   ?
         0  0   0   0
         1  0   1   ?
         ?  0   ?   ?   <- result
        self

        backwards & (this one):
                  self
            0   1   ?
         0  ?   0   ?
         1  X   1   1
         ?  ?   ?   ?   <- other
        result

        (X marks an inconsistent result).

        We can see that we only learn something about other at the places
        where a bit from self is 1. At those places, the corresponding bit in
        other has to be the corresponding bit in result.
        """

        tvalue, tmask, valid = self._tnum_and_backwards(result)
        if not valid:
            raise InvalidLoop("inconsistency in and_bound_backwards")
        return IntBound.from_knownbits(tvalue, tmask)

    @always_inline
    def _tnum_and_backwards(self, result):
        # in all the places where the result is 1 both arguments have to 1. in
        # the places where result is 0, other has to be 0 iff self is known 1.
        tvalue = result.tvalue
        tmask = ((~self.tvalue) | result.tmask) & ~tvalue
        # if we have a place where result is 1 but self is 0, then we are
        # inconsistent
        inconsistent = result.tvalue & ~self.tmask & ~self.tvalue
        return tvalue, tmask, inconsistent == 0

    def or_bound_backwards(self, result):
        """
        result_int == int_or(self, other)
        We want to refine our knowledge about other
        using this information

        regular |:
                  other
         &  0   1   ?
         0  0   1   ?
         1  1   1   1
         ?  ?   1   ?   <- result
        self

        backwards | (this one):
                  self
            0   1   ?
         0  0   X   0
         1  1   ?   ?
         ?  ?   ?   ?   <- other (where X=invalid)
        result

        """
        tvalue, tmask, valid = self._tnum_or_backwards(result)
        if not valid:
            raise InvalidLoop("inconsistency in or_bound_backwards")
        return IntBound.from_knownbits(tvalue, tmask)

    @always_inline
    def _tnum_or_backwards(self, result):
        # in all the places where the result is 0 both arguments have to be 0.
        zeros = (~result.tmask & ~result.tvalue)
        # apart from that, in the places where self is 0 and where result is 1
        # other must be 1
        tvalue = (result.tvalue & ~self.tvalue & ~self.tmask)
        tmask = ~(zeros | tvalue)
        # if we have a place where result is 0 but self is 1, then we are
        # inconsistent
        inconsistent = self.tvalue & zeros
        return tvalue, tmask, inconsistent == 0

    def rshift_bound_backwards(self, other):
        """
        Performs a `urshift`/`rshift` backwards on `self`. Basically
        left-shifts `self` by `other` binary digits, filling the lower part
        with ?, and returns the result.
        """
        if not other.is_constant():
            return IntBound.unbounded()
        c_other = other.get_constant_int()
        tvalue, tmask = TNUM_UNKNOWN
        if 0 <= c_other < LONG_BIT:
            tvalue = self.tvalue << r_uint(c_other)
            tmask = self.tmask << r_uint(c_other)
            # shift ? in from the right,
            tmask |= (r_uint(1) << r_uint(c_other)) - 1
        return IntBound.from_knownbits(tvalue, tmask)
    urshift_bound_backwards = rshift_bound_backwards

    def lshift_bound_backwards(self, other):
        """
        Performs a `lshift` backwards on `self`. Basically right-shifts `self`
        by `other` binary digits, filling the upper part with ?, and returns
        the result.
        """
        if not other.is_constant():
            return IntBound.unbounded()
        c_other = r_uint(other.get_constant_int())
        tvalue, tmask = TNUM_UNKNOWN
        if 0 <= c_other < LONG_BIT:
            tvalue = self.tvalue >> c_other
            tmask = self.tmask >> c_other
            # shift ? in from the left,
            s_tmask = ~(r_uint(-1) >> c_other)
            tmask |= s_tmask
            inconsistent = self.tvalue & ((1 << c_other) - 1)
            if inconsistent:
                raise InvalidLoop("lshift_bound_backwards inconsistent known bits")
        return IntBound.from_knownbits(tvalue, tmask)

    def shrink(self):
        """ Shrink the bounds and the knownbits to be more precise, but without
        changing the set of integers that is represented by self.

        Here's a diagram to show what is happening. This is the number line:
        MININT <---------0-----------------------------------------------> MAXINT

        We have a range in the number line
                           [lower     ...       upper]

        We also known bits, they represent a set of ints maybe looking like this:
                X X X X         X X X X         X X X X         X X X X
        (an X means the number matches the known bits, ' ' means it doesn't)

        Note that the lower and upper bounds could be more precise (ie bigger
        and smaller, respectively), because they don't match the known bits.
        Also, there are numbers that match the known bits to the left of lower
        and the right of upper, that are excluded by the range and thus
        unnecessary. We want to fix both of that.

        First we shrink the bounds so that they both match the known bits,
        then things look like this:
                                [lower   ...   upper]
                X X X X         X X X X         X X X X         X X X X
        This is achieved by moving lower to the right to the first number >=
        lower that matches the known bits (and mutatis mutandis for upper).

        Afterwards we use the information from the bounds to add more known
        bits. Having done that, things look maybe something like this:
                                [lower   ...   upper]
                                X X X X         X X X X
        Then we're done with shrinking.

        The set that is described by these two pieces of information together
        is neither expressible as purely a range, nor purely by known bits.
        It looks like this:
                                X X X X         X X X
        The set did not change through this process, but the bounds and the
        known bits becoming more precise makes it possible to compute more
        precise results when doing further operations with self.
        """
        # there's a proof in test_z3intbound that one pass of shrinking is
        # always enough. let's still assert that a second pass doesn't change
        # anything.
        changed = self._shrink_bounds_by_knownbits()
        changed |= self._shrink_knownbits_by_bounds()
        if not changed:
            return changed
        changed_again = self._shrink_bounds_by_knownbits()
        changed_again |= self._shrink_knownbits_by_bounds()
        assert not changed_again
        return changed

    def _shrink_bounds_by_knownbits(self):
        """
        Shrinks the bounds by the known bits.
        """
        # lower bound
        min_by_knownbits = self._get_minimum_signed_by_knownbits_atleast(self.lower)
        max_by_knownbits = self._get_maximum_signed_by_knownbits_atmost(self.upper)
        if min_by_knownbits > max_by_knownbits:
            raise InvalidLoop("range and knownbits contradict each other")
        changed = self.lower < min_by_knownbits or self.upper > max_by_knownbits
        if changed:
            self.lower = min_by_knownbits
            self.upper = max_by_knownbits
        return changed

    def _shrink_knownbits_by_bounds(self):
        """
        Infers known bits from the bounds. Basically fills a common prefix from
        lower and upper bound into the knownbits.
        """
        tvalue, tmask, valid = self._tnum_improve_knownbits_by_bounds()
        if not valid:
            raise InvalidLoop("knownbits and bounds don't agree")
        changed = self.tvalue != tvalue or self.tmask != tmask
        if changed:
            self.tmask = tmask
            self.tvalue = tvalue
        return changed

    @always_inline
    def _tnum_implied_by_bounds(self):
        # calculate higher bit mask by bounds
        hbm_bounds = leading_zeros_mask(
                self.r_uint(self.lower) ^ self.r_uint(self.upper))
        bounds_common = self.r_uint(self.lower) & hbm_bounds
        tmask = ~hbm_bounds
        return unmask_zero(bounds_common, tmask), tmask

    @always_inline
    def _tnum_improve_knownbits_by_bounds(self):
        # knownbits that are implied by the bounds
        tvalue, tmask = self._tnum_implied_by_bounds()
        # intersect them with the current knownbits
        return self._tnum_intersect(tvalue, tmask)

    def _debug_check(self):
        """
        Very simple debug check. Returns `True` iff the span of knownbits and
        the span of the bounds have a non-empty intersection. That does not
        guarantee for the actual concrete value set to contain any values!
        """
        assert self.lower <= self.upper
        min_knownbits = self._get_minimum_signed_by_knownbits()
        max_knownbits = self._get_maximum_signed_by_knownbits()
        if not min_knownbits <= self.upper:
            return False
        if not max_knownbits >= self.lower:
            return False
        # just to make sure
        if not min_knownbits <= max_knownbits:
            return False
        # make sure the set is not empty
        if self.is_constant():
            # does one constraint exclude the constant value?
            val = self.get_constant_int()
            if min_knownbits > val or max_knownbits < val \
               or self.lower > val or self.upper < val:
                return False
        else:
            # we have no constant, so keep checking
            u_lower = r_uint(self.lower)
            u_upper = r_uint(self.upper)
            # check if bounds common prefix agrees with known-bits
            hbm_bounds = leading_zeros_mask(u_lower ^ u_upper)
            bounds_common_prefix = u_lower & hbm_bounds
            if unmask_zero(bounds_common_prefix, self.tmask) != self.tvalue & hbm_bounds:
                return False
            # for the rest of the bunch, check by minima/maxima with threshold.
            #   (side note: the whole check can be reduced to this, but for the
            #    sake of robustness we want to keep the other checks above.)
            if self._get_minimum_signed_by_knownbits_atleast(self.lower) > self.upper \
               or self._get_maximum_signed_by_knownbits_atmost(self.upper) < self.lower:
                return False
        return True

    def knownbits_string(self, unk_sym='?'):
        """
        Returns a string representation about the knownbits part of this
        abstract integer. You can give any symbol or string for the "unknown
        bits" (default: '?'), the other digits are written as '1' and '0'.
        """
        results = []
        for bit in range(LONG_BIT):
            if self.tmask & (1 << bit):
                results.append(unk_sym)
            else:
                results.append(str((self.tvalue >> bit) & 1))
        results.reverse()
        return "".join(results)


def flip_msb(val_uint):
    return val_uint ^ r_uint(MININT)

def is_valid_tnum(tvalue, tmask):
    """
    Returns `True` iff `tvalue` and `tmask` would be valid tri-state number
    fields of an abstract integer, meeting all conventions and requirements.
    """
    if not isinstance(tvalue, r_uint):
        return False
    if not isinstance(tmask, r_uint):
        return False
    return 0 == (r_uint(tvalue) & r_uint(tmask))

def leading_zeros_mask(n):
    """
    calculates a bitmask in which only the leading zeros of `n` are set (1).
    """
    return ~next_pow2_m1(n)

def lowest_set_bit_only(val_uint):
    """
    Returns an val_int, but with all bits deleted but the lowest one that was
    set.
    """
    #assert isinstance(val_uint, r_uint)
    working_val = ~val_uint
    increased_val = working_val + 1
    result = (working_val^increased_val) & val_uint
    return result

def min4(t):
    """
    Returns the minimum of the values in the quadruplet t.
    """
    return min(min(t[0], t[1]), min(t[2], t[3]))

def max4(t):
    """
    Returns the maximum of the values in the quadruplet t.
    """
    return max(max(t[0], t[1]), max(t[2], t[3]))

def msbonly(v):
    """
    Returns `v` with all bits except the most significant bit set to 0 (zero).
    """
    return v & (1 << (LONG_BIT-1))

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

def unmask_one(value, mask):
    """
    Sets all unknowns determined by `mask` in `value` bit-wise to 1 (one) and
    returns the result.
    """
    return value | mask

def unmask_zero(value, mask):
    """
    Sets all unknowns determined by `mask` in `value` bit-wise to 0 (zero) and
    returns the result.
    """
    return value & ~mask

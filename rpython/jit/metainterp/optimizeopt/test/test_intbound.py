import pytest

from copy import copy
import sys
import operator

from rpython.jit.metainterp.optimizeopt.intutils import (IntBound,
     next_pow2_m1, msbonly, MININT, MAXINT, lowest_set_bit_only,
     leading_zeros_mask)
from rpython.jit.metainterp.optimizeopt.info import (INFO_NONNULL,
     INFO_UNKNOWN, INFO_NULL)
from rpython.rlib.rarithmetic import LONG_BIT, ovfcheck, r_uint, intmask
from rpython.jit.metainterp.optimize import InvalidLoop

from hypothesis import given, strategies, example, seed, assume

special_values_set = (
    range(100) + range(-1, -100, -1) +
    [2 ** i for i in range(1, LONG_BIT)] +
    [-2 ** i for i in range(1, LONG_BIT)] +
    [2 ** i - 1 for i in range(1, LONG_BIT)] +
    [-2 ** i - 1 for i in range(1, LONG_BIT)] +
    [2 ** i + 1 for i in range(1, LONG_BIT)] +
    [-2 ** i + 1 for i in range(1, LONG_BIT)] +
    [sys.maxint, -sys.maxint-1]
)

special_values = strategies.sampled_from(
    [int(v) for v in special_values_set if type(int(v)) is int])

pos_special_values_set = (
    range(0, 100) +
    [sys.maxint] +
    [2 ** i for i in range(1, LONG_BIT)] +
    [2 ** i - 1 for i in range(1, LONG_BIT)] +
    [2 ** i + 1 for i in range(1, LONG_BIT)])

pos_special_values = strategies.sampled_from(
    [int(v) for v in pos_special_values_set if type(int(v)) is int])

pos_relatively_small_values = strategies.sampled_from(
    [int(v) for v in range(0, 128)])

ints = strategies.builds(
    int, # strategies.integers sometimes returns a long?
    special_values | strategies.integers(
    min_value=int(-sys.maxint-1), max_value=sys.maxint))

ints_or_none = strategies.none() | ints

pos_ints = strategies.builds(
    int,
    pos_special_values | strategies.integers(
    min_value=int(0), max_value=sys.maxint))

def bound_eq(a, b):
    return a.__dict__ == b.__dict__

def bound(a, b):
    if a is None and b is None:
        return IntBound.unbounded()
    elif a is None:
        return IntBound(upper=b)
    elif b is None:
        return IntBound(lower=a)
    else:
        return IntBound(a, b)

def const(a):
    return IntBound.from_constant(a)


def build_bound_with_contained_number(a, b, c):
    a, b, c = sorted([a, b, c])
    r = bound(a, c)
    assert r.contains(b)
    return r, b

def build_some_bits_known(a, b):
    return knownbits(a&~b, b), a

def build_some_bits_known_bounded(res_value, tmask, data):
    # generate a fully random value and a tmask of known bits
    tmask = r_uint(tmask)
    b = IntBound.from_knownbits(tvalue=r_uint(res_value), tmask=tmask, do_unmask=True)
    assert b.contains(res_value)
    # now after construction b has the bounds that are implied by the known
    # bits. to make the bounds be tighter than what is implied by the
    # knownbits, shrink them a bit, but make sure that res_value stays inside the bounds
    space_at_bottom = res_value - b.lower
    if space_at_bottom:
        shrink_by = data.draw(strategies.integers(0, space_at_bottom - 1))
        b.make_ge_const(int(b.lower + shrink_by))
        assert b.contains(res_value)
    space_at_top = b.upper - res_value
    if space_at_top:
        shrink_by = data.draw(strategies.integers(0, space_at_top - 1))
        b.make_le_const(int(b.upper - shrink_by))
        assert b.contains(res_value)
    repr(b) # must not fail
    return b, res_value

def build_two_ints_tuple(a, b):
    return (a, b)

def build_valid_mask_value_pair(a, b):
    return (a & ~b, b)

unbounded = strategies.builds(
    lambda x: (bound(None, None), int(x)),
    ints
)

lower_bounded = strategies.builds(
    lambda x, y: (bound(min(x, y), None), max(x, y)),
    ints, ints
)

upper_bounded = strategies.builds(
    lambda x, y: (bound(None, max(x, y)), min(x, y)),
    ints, ints
)

bounded = strategies.builds(
    build_bound_with_contained_number,
    ints, ints, ints
)

constant = strategies.builds(
    lambda x: (const(x), x),
    ints
)

some_bits_known = strategies.builds(
    build_some_bits_known,
    ints, ints
)

some_bits_known_bounded = strategies.builds(
    build_some_bits_known_bounded,
    ints, ints, strategies.data(),
)

random_ints_tuple = strategies.builds(
    build_two_ints_tuple,
    ints, ints
)

random_valid_mask_value_pair = strategies.builds(
    build_valid_mask_value_pair,
    ints, ints
)

maybe_valid_value_mask_pair = strategies.one_of(
    random_ints_tuple, random_valid_mask_value_pair
)

# most generic strategy producing all kinds of IntBound instances
knownbits_and_bound_with_contained_number = strategies.one_of(
    # roughly ordered from more specific to more general
    constant,                # fully constant
    lower_bounded,           # just a lower bound
    upper_bounded,           # just an upper bound
    bounded,                 # both upper and lower bound
    some_bits_known,         # just a tnum (with only implied bounds)
    some_bits_known_bounded, # a tnum with tighter bounds, not necessarily implied
    unbounded                # nothing known at all
)

shift_amount = strategies.builds(
    lambda x: (const(x), x),
    strategies.integers(min_value=0, max_value=LONG_BIT)
) | strategies.builds(
    build_bound_with_contained_number,
    *(strategies.integers(min_value=0, max_value=LONG_BIT), ) * 3
)


nbr = range(-5, 6)
nnbr = list(set(range(-9, 10)) - set(nbr))

def some_bounds():
    brd = [None] + range(-2, 3)
    for lower in brd:
        for upper in brd:
            if lower is not None and upper is not None and lower > upper:
                continue
            yield (lower, upper, bound(lower, upper))

def some_bits():
    tvals = nbr
    tmsks = nbr
    for tval in tvals:
        for tmsk in tmsks:
            yield (tval, tmsk, knownbits(tval, tmsk, True))

def test_known():
    for lower, upper, b in some_bounds():
        inside = []
        border = []
        for n in nbr:
            if (lower is None or n >= lower) and \
               (upper is None or n <= upper):
                if n == lower or n ==upper:
                    border.append(n)
                else:
                    inside.append(n)

        for n in nbr:
            c = const(n)
            if n in inside:
                assert b.contains(n)
                assert not b.known_lt(c)
                assert not b.known_gt(c)
                assert not b.known_le(c)
                assert not b.known_ge(c)
                assert not b.known_lt_const(n)
                assert not b.known_gt_const(n)
                assert not b.known_le_const(n)
                assert not b.known_ge_const(n)
            elif n in border:
                assert b.contains(n)
                if n == upper:
                    assert b.known_le(const(upper))
                    assert b.known_le_const(upper)
                else:
                    assert b.known_ge_const(lower)
                    assert b.known_ge(const(lower))
            else:
                assert not b.contains(n)
                some = (border + inside)[0]
                if n < some:
                    assert b.known_gt(c)
                else:
                    assert b.known_lt(c)


def test_make():
    for _, _, b1 in some_bounds():
        for _, _, b2 in some_bounds():
            lt = IntBound.unbounded()
            lt.make_lt(b1)
            lt.make_lt(b2)
            for n in nbr:
                c = const(n)
                if b1.known_le(c) or b2.known_le(c):
                    assert lt.known_lt(c)
                else:
                    assert not lt.known_lt(c)
                assert not lt.known_gt(c)
                assert not lt.known_ge(c)

            gt = IntBound.unbounded()
            gt.make_gt(b1)
            try:
                gt.make_gt(b2)
            except InvalidLoop: # 
                pass
            else:
                for n in nbr:
                    c = const(n)
                    if b1.known_ge(c) or b2.known_ge(c):
                        assert gt.known_gt(c)
                    else:
                        assert not gt.known_gt(c)
                assert not gt.known_lt(c)
                assert not gt.known_le(c)

            le = IntBound.unbounded()
            le.make_le(b1)
            try:
                le.make_le(b2)
            except InvalidLoop:
                pass
            else:
                for n in nbr:
                    c = const(n)
                    if b1.known_le(c) or b2.known_le(c):
                        assert le.known_le(c)
                    else:
                        assert not le.known_le(c)
                    assert not le.known_gt(c)
                    assert not le.known_ge(c)


            ge = IntBound.unbounded()
            ge.make_ge(b1)
            try:
                ge.make_ge(b2)
            except InvalidLoop: # 
                pass
            else:
                for n in nbr:
                    c = const(n)
                    if b1.known_ge(c) or b2.known_ge(c):
                        assert ge.known_ge(c)
                    else:
                        assert not ge.known_ge(c)
                    assert not ge.known_lt(c)
                    assert not ge.known_le(c)

            gl = IntBound.unbounded()
            gl.make_ge(b1)
            try:
                gl.make_le(b2)
            except InvalidLoop: # 
                pass
            else:
                for n in nbr:
                    c = const(n)
                    if b1.known_ge(c):
                        assert gl.known_ge(c)
                    else:
                        assert not gl.known_ge(c)
                        assert not gl.known_gt(c)
                    if  b2.known_le(c):
                        assert gl.known_le(c)
                    else:
                        assert not gl.known_le(c)
                        assert not gl.known_lt(c)

def test_make_invalid_loop_cases():
    b1 = IntBound.unbounded()
    b2 = IntBound.from_constant(MININT)
    with pytest.raises(InvalidLoop):
        b1.make_lt(b2)

    b1 = IntBound.unbounded()
    b2 = IntBound.from_constant(MAXINT)
    with pytest.raises(InvalidLoop):
        b1.make_gt(b2)

    b1 = IntBound.nonnegative()
    with pytest.raises(InvalidLoop):
        b1.make_eq_const(-1)

def test_make_ne():
    ge = IntBound.unbounded()
    res = ge.make_ne_const(MININT)
    assert res
    res = ge.make_ne_const(MININT)
    assert not res
    assert not ge.contains(MININT)
    assert ge.contains(MININT + 1)
    assert ge.contains(MAXINT)

def test_intersect():
    for _, _, b1 in some_bounds():
        for _, _, b2 in some_bounds():
            if b1.known_gt(b2) or b1.known_lt(b2):
                # no overlap
                continue
            b = copy(b1)
            b.intersect(b2)
            for n in nbr:
                if b1.contains(n) and b2.contains(n):
                    assert b.contains(n)
                else:
                    assert not b.contains(n)

def test_intersect_bug():
    b1 = bound(17, 17)
    b2 = bound(1, 1)
    with pytest.raises(InvalidLoop):
        b1.intersect(b2)

def test_intersect_contradiction_range_knownbits():
    b1 = IntBound(-1, 0)
    b2 = IntBound.from_knownbits(r_uint(0b11100), r_uint(-0b1100000))
    with pytest.raises(InvalidLoop):
        b1.intersect(b2)

def test_intersect_contradiction_range_knownbits2():
    # more cases
    b1 = IntBound(0, 256)
    b2 = IntBound.from_knownbits(r_uint(0b100000001), r_uint(-0b100000010))
    b = b1.clone()
    with pytest.raises(InvalidLoop):
        b.intersect(b2)

    b1 = IntBound(1, 3)
    b2 = IntBound.from_knownbits(r_uint(0b0), r_uint(-0b101100)) # 0b?...?0?0?00
    b = b1.clone()
    with pytest.raises(InvalidLoop):
        b.intersect(b2)

def test_add_bound():
    for _, _, b1 in some_bounds():
        for _, _, b2 in some_bounds():
            b3 = b1.add_bound(b2)
            for n1 in nbr:
                for n2 in nbr:
                    if b1.contains(n1) and b2.contains(n2):
                        assert b3.contains(n1 + n2)

    a=bound(2, 4).add_bound(bound(1, 2))
    assert not a.contains(2)
    assert not a.contains(7)

def test_add_bound_bug():
    b = bound(MININT, MAXINT)
    bval = MAXINT
    assert b.contains(bval)
    r = b.add_bound(IntBound.from_constant(1))
    rval = intmask(r_uint(bval)+r_uint(1))
    assert r.contains(rval)

def test_mul_bound():
    for _, _, b1 in some_bounds():
        for _, _, b2 in some_bounds():
            b3 = b1.mul_bound(b2)
            for n1 in nbr:
                for n2 in nbr:
                    if b1.contains(n1) and b2.contains(n2):
                        assert b3.contains(n1 * n2)

    a=bound(2, 4).mul_bound(bound(1, 2))
    assert not a.contains(1)
    assert not a.contains(9)

    a=bound(-3, 2).mul_bound(bound(1, 2))
    assert not a.contains(-7)
    assert not a.contains(5)
    assert a.contains(-6)
    assert a.contains(4)

    a=bound(-3, 2).mul_bound(bound(-1, -1))
    for i in range(-2,4):
        assert a.contains(i)
    assert not a.contains(4)
    assert not a.contains(-3)

def test_shift_bound():
    for _, _, b1 in some_bounds():
        for _, _, b2 in some_bounds():
            bleft = b1.lshift_bound(b2)
            bright = b1.rshift_bound(b2)
            for n1 in nbr:
                for n2 in range(10):
                    if b1.contains(n1) and b2.contains(n2):
                        assert bleft.contains(n1 << n2)
                        assert bright.contains(n1 >> n2)

def test_shift_overflow():
    b10 = IntBound(0, 10)
    b100 = IntBound(0, 100)
    bmax = IntBound(0, sys.maxint/2)
    assert b10.lshift_bound(b100).upper == MAXINT
    assert bmax.lshift_bound(b10).upper == MAXINT
    assert b10.lshift_bound(b10).upper == 10 << 10
    for b in (b10, b100, bmax, IntBound.from_constant(0)):
        for shift_count_bound in (IntBound(7, LONG_BIT), IntBound(-7, 7)):
            assert b.rshift_bound(shift_count_bound).upper == MAXINT

def test_div_bound():
    for _, _, b1 in some_bounds():
        for _, _, b2 in some_bounds():
            b3 = b1.py_div_bound(b2)
            for n1 in nbr:
                for n2 in nbr:
                    if b1.contains(n1) and b2.contains(n2):
                        if n2 != 0:
                            assert b3.contains(n1 / n2)   # Python-style div

    a=bound(2, 4).py_div_bound(bound(1, 2))
    assert not a.contains(0)
    assert not a.contains(5)

    a=bound(-3, 2).py_div_bound(bound(1, 2))
    assert not a.contains(-4)
    assert not a.contains(3)
    assert a.contains(-3)
    assert a.contains(0)

def test_mod_bound():
    for _, _, b1 in some_bounds():
        for _, _, b2 in some_bounds():
            b3 = b1.mod_bound(b2)
            for n1 in nbr:
                for n2 in nbr:
                    if b1.contains(n1) and b2.contains(n2):
                        if n2 != 0:
                            assert b3.contains(n1 % n2)   # Python-style div

def test_sub_bound():
    for _, _, b1 in some_bounds():
        for _, _, b2 in some_bounds():
            b3 = b1.sub_bound(b2)
            for n1 in nbr:
                for n2 in nbr:
                    if b1.contains(n1) and b2.contains(n2):
                        assert b3.contains(n1 - n2)

    a=bound(2, 4).sub_bound(bound(1, 2))
    assert not a.contains(-1)
    assert not a.contains(4)

    a = IntBound.from_constant(0).sub_bound(bound(0, None))
    assert a.lower == -MAXINT
    assert a.upper == 0

    a = IntBound.from_constant(0).sub_bound(bound(None, 0))
    assert a.lower == MININT
    assert a.upper == MAXINT


def test_sub_bound_bug():
    b = bound(MININT, MAXINT)
    bval = MININT
    assert b.contains(bval)
    r = b.sub_bound(IntBound.from_constant(1))
    rval = intmask(r_uint(bval)-r_uint(1))
    assert r.contains(rval)

def test_and_bound():
    for _, _, b1 in some_bounds():
        for _, _, b2 in some_bounds():
            b3 = b1.and_bound(b2)
            for n1 in nbr:
                for n2 in nbr:
                    if b1.contains(n1) and b2.contains(n2):
                        assert b3.contains(n1 & n2)

def test_and_bound_example():
    b1 = IntBound(0, 16)
    b2 = IntBound.unbounded()
    b3 = b1.and_bound(b2)
    assert bound_eq(b3, b1)

def test_or_bound():
    for _, _, b1 in some_bounds():
        for _, _, b2 in some_bounds():
            b3 = b1.or_bound(b2)
            for n1 in nbr:
                for n2 in nbr:
                    if b1.contains(n1) and b2.contains(n2):
                        assert b3.contains(n1 | n2)

def test_xor_bound():
    for _, _, b1 in some_bounds():
        for _, _, b2 in some_bounds():
            b3 = b1.xor_bound(b2)
            for n1 in nbr:
                for n2 in nbr:
                    if b1.contains(n1) and b2.contains(n2):
                        assert b3.contains(n1 ^ n2)


def test_next_pow2_m1():
    assert next_pow2_m1(r_uint(0)) == r_uint(0)
    assert next_pow2_m1(r_uint(1)) == r_uint(1)
    assert next_pow2_m1(r_uint(7)) == r_uint(7)
    assert next_pow2_m1(r_uint(256)) == r_uint(511)
    assert next_pow2_m1(r_uint(255)) == r_uint(255)
    assert next_pow2_m1(r_uint(80)) == r_uint(127)
    assert next_pow2_m1(r_uint((1 << 32) - 5)) == r_uint((1 << 32) - 1)
    assert next_pow2_m1(r_uint((1 << 64) - 1)) == r_uint((1 << 64) - 1)

def test_leading_zeros_mask():
    assert leading_zeros_mask(r_uint(0)) == r_uint(-1)
    assert leading_zeros_mask(r_uint(-1)) == r_uint(0)
    assert leading_zeros_mask(r_uint(0b100)) == ~r_uint(0b111)
    assert leading_zeros_mask(r_uint(MAXINT)) == ~r_uint(MAXINT)

def test_shrink_bug():
    lower = 1
    upper = MAXINT - 1
    assert r_uint(lower) ^ r_uint(upper) == r_uint(MAXINT)
    b = IntBound(lower, upper, do_shrinking=False)
    b._shrink_knownbits_by_bounds()
    # the sign bit (highest bit) must be 0, because all values 1 <= x <= MAXINT - 1 are positive
    assert b.tmask == r_uint(MAXINT) # 0?.....?
    assert b.tvalue == r_uint(0)

def test_invert_bound():
    for _, _, b1 in some_bounds():
        b2 = b1.invert_bound()
        for n1 in nbr:
            if b1.contains(n1):
                assert b2.contains(~n1)

def test_neg_bound():
    for _, _, b1 in some_bounds():
        b2 = b1.neg_bound()
        for n1 in nbr:
            if b1.contains(n1):
                assert b2.contains(-n1)

def test_widen():
    for _, _, b1 in some_bounds():
        b2 = b1.widen()
        b3 = b2.clone()
        b3.intersect(b1)
        bound_eq(b3, b1)
    b = bound(MININT + 1, MAXINT).widen()
    assert bound_eq(b, bound(None, None))
    b = bound(MININT, MAXINT - 1).widen()
    assert bound_eq(b, bound(None, None))
    b = bound(-10, 10)
    b1 = b.widen()
    assert bound_eq(b, b1)


@given(knownbits_and_bound_with_contained_number,
       knownbits_and_bound_with_contained_number,
       strategies.sampled_from(("lt", "le", "gt", "ge")))
def test_make_random(t1, t2, name):
    def d(b):
        return b.lower, b.upper, b.tvalue, b.tmask
    b1, n1 = t1
    b2, n2 = t2

    meth = getattr(IntBound, "make_" + name)
    b = b1.clone()
    try:
        changed = meth(b, b2)
    except InvalidLoop:
        assert not getattr(operator, name)(n1, n2)
        return
    data = d(b)
    assert not meth(b, b2)
    assert data == d(b) # idempotent
    assert changed == (d(b1) != d(b))
    if not b.contains(n1):
        assert not getattr(operator, name)(n1, n2)

def test_make_unsigned_less_example():
    b1 = IntBound(0, 10)
    b2 = IntBound.unbounded()
    res = b2.make_unsigned_le(b1)
    assert res is True
    assert b2.known_nonnegative()
    assert b2.known_le_const(10)

    b1 = IntBound(0, 10)
    b2 = IntBound.unbounded()
    res = b2.make_unsigned_lt(b1)
    assert res is True
    assert b2.known_nonnegative()
    assert b2.known_lt_const(10)

    b1 = IntBound(0, 0)
    b2 = IntBound.unbounded()
    with pytest.raises(InvalidLoop):
        b2.make_unsigned_lt(b1)

def test_make_unsigned_greater_example():
    # we can learn something if b2 is negative
    b1 = IntBound.unbounded()
    b2 = IntBound(lower=-100, upper=-2)
    res = b1.make_unsigned_ge(b2)
    assert res is True
    assert b1.known_lt_const(0)
    assert b1.known_ge_const(-100)

    b1 = IntBound.unbounded()
    b2 = IntBound(lower=-100, upper=-2)
    res = b1.make_unsigned_gt(b2)
    assert res is True
    assert b1.known_lt_const(0)
    assert b1.known_gt_const(-100)

    # we can also learn something if they are both nonnegative (then the logic
    # just falls back to signed comparisons)
    b1 = IntBound.nonnegative()
    b2 = IntBound(2, 100)
    res = b1.make_unsigned_ge(b2)
    assert res is True
    assert b1.known_ge_const(2)

    b1 = IntBound.nonnegative()
    b2 = IntBound(lower=5)
    res = b1.make_unsigned_gt(b2)
    assert res is True
    assert b1.known_gt_const(5)

@example(t1=(IntBound(MININT, 0), 0), t2=(IntBound(-4, -3), -3), name='gt')
@given(knownbits_and_bound_with_contained_number,
       knownbits_and_bound_with_contained_number,
       strategies.sampled_from(("lt", "le", "gt", "ge")))
def test_make_unsigned_random(t1, t2, name):
    def d(b):
        return b.lower, b.upper, b.tvalue, b.tmask
    b1, n1 = t1
    b2, n2 = t2

    meth = getattr(IntBound, "make_unsigned_" + name)
    b = b1.clone()
    try:
        changed = meth(b, b2)
    except InvalidLoop:
        # it wasn't possible to make b1 < b2. therefore the concrete number n1
        # must also not be < n2
        assert not getattr(operator, name)(r_uint(n1), r_uint(n2))
        return
    data = d(b)
    assert not meth(b, b2)
    assert data == d(b) # idempotent
    assert changed == (d(b1) != d(b))
    if not b.contains(n1):
        assert changed
        # if n1 was removed by the make_unsigned_lt call, then it must not be
        # smaller than n2
        assert not getattr(operator, name)(r_uint(n1), r_uint(n2))


@given(knownbits_and_bound_with_contained_number)
def test_add_zero_is_zero_random(t1):
    b1, n1 = t1
    # first check that 0 + b1 is b1
    b1viaadd0 = b1.add_bound(IntBound.from_constant(0))
    assert bound_eq(b1, b1viaadd0)


@given(knownbits_and_bound_with_contained_number, knownbits_and_bound_with_contained_number)
def test_add_random(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    b3 = b1.add_bound(b2)
    # the result bound works for unsigned addition, regardless of overflow
    assert b3.contains(intmask(r_uint(n1) + r_uint(n2)))

    b3noovf = b1.add_bound_no_overflow(b2)
    try:
        r = ovfcheck(n1 + n2)
    except OverflowError:
        assert not b1.add_bound_cannot_overflow(b2)
    else:
        assert b3.contains(r)
        assert b3noovf.contains(r)


@given(knownbits_and_bound_with_contained_number)
def test_sub_zero_is_zero_random(t1):
    b1, n1 = t1
    # first check that b1 - 0 is b1
    b1viasub0 = b1.sub_bound(IntBound.from_constant(0))
    assert bound_eq(b1, b1viasub0)

@example((bound(-100, None), -99), (bound(None, -100), -100))
@given(knownbits_and_bound_with_contained_number, knownbits_and_bound_with_contained_number)
def test_sub_random(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    print b1, n1
    print b2, n2
    b3 = b1.sub_bound(b2)
    # the result bound works for unsigned subtraction, regardless of overflow
    assert b3.contains(intmask(r_uint(n1) - r_uint(n2)))

    b3noovf = b1.sub_bound_no_overflow(b2)
    try:
        r = ovfcheck(n1 - n2)
    except OverflowError:
        assert not b1.sub_bound_cannot_overflow(b2)
    else:
        assert b3.contains(r)
        assert b3noovf.contains(r)


@given(knownbits_and_bound_with_contained_number, knownbits_and_bound_with_contained_number)
def test_mul_random(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    b3 = b1.mul_bound(b2)
    try:
        r = ovfcheck(n1 * n2)
    except OverflowError:
        assert not b1.mul_bound_cannot_overflow(b2)
    else:
        assert b3.contains(r)

@given(knownbits_and_bound_with_contained_number, knownbits_and_bound_with_contained_number)
def test_div_random(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    b3 = b1.py_div_bound(b2)
    if n1 == -sys.maxint-1 and n2 == -1:
        return # overflow
    if n2 != 0:
        assert b3.contains(n1 / n2)   # Python-style div

def test_mod_bound_example():
    b1 = IntBound()
    b2 = IntBound(-20, 10)
    r = b1.mod_bound(b2)
    assert r.known_gt_const(-20)
    assert r.known_lt_const(10)

    b1 = IntBound()
    b2 = IntBound(upper=10)
    r = b1.mod_bound(b2)
    assert r.known_gt_const(MININT)
    assert r.known_lt_const(10)

    b1 = IntBound()
    b2 = IntBound(lower=10)
    r = b1.mod_bound(b2)
    assert r.known_ge_const(0)
    assert r.known_lt_const(MAXINT)

    b1 = IntBound()
    b2 = IntBound(upper=-10)
    r = b1.mod_bound(b2)
    assert r.known_le_const(0)
    assert r.known_gt_const(MININT)

    b1 = IntBound()
    b2 = IntBound(lower=-10)
    r = b1.mod_bound(b2)
    assert r.known_gt_const(-10)
    assert r.known_lt_const(MAXINT)

@given(knownbits_and_bound_with_contained_number, knownbits_and_bound_with_contained_number)
def test_mod_bound_random(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    b3 = b1.mod_bound(b2)
    if n1 == -sys.maxint-1 and n2 == -1:
        return # overflow
    if n2 != 0:
        assert b3.contains(n1 % n2)   # Python-style mod

@given(knownbits_and_bound_with_contained_number, shift_amount)
def test_lshift_random(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    b3 = b1.lshift_bound(b2)
    try:
        r = ovfcheck(n1 << n2)
    except OverflowError:
        assert not b1.lshift_bound_cannot_overflow(b2)
    else:
        b3.contains(r)
    assert b3.contains(intmask(r_uint(n1) << r_uint(n2)))

@given(knownbits_and_bound_with_contained_number, pos_relatively_small_values)
def test_lshift_const_random(t1, t2):
    b1, n1 = t1
    b2 = IntBound.from_constant(t2)
    r = b1.lshift_bound(b2)
    # this works for left-shift, but not for right-shift!
    assert r.contains(intmask(r_uint(n1) << r_uint(t2)))

@given(knownbits_and_bound_with_contained_number, knownbits_and_bound_with_contained_number)
def test_and_random(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    b3 = b1.and_bound(b2)
    r = n1 & n2
    assert b3.contains(r)

@given(knownbits_and_bound_with_contained_number, knownbits_and_bound_with_contained_number)
def test_or_random(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    b3 = b1.or_bound(b2)
    r = n1 | n2
    assert b3.contains(r)

@given(knownbits_and_bound_with_contained_number, knownbits_and_bound_with_contained_number)
def test_xor_random(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    b3 = b1.xor_bound(b2)
    r = n1 ^ n2
    assert b3.contains(r)

@given(knownbits_and_bound_with_contained_number)
def test_invert_random(t1):
    b1, n1 = t1
    b2 = b1.invert_bound()
    assert b2.contains(~n1)

@given(knownbits_and_bound_with_contained_number)
@example((IntBound.from_constant(MININT), MININT))
@example((IntBound(upper=-100), MININT))
@example((IntBound(MININT, MININT+9), MININT))
def test_neg_random(t1):
    b1, n1 = t1
    b2 = b1.neg_bound()
    if (n1 != MININT):
        assert b2.contains(intmask(-n1))

    # check that it's always correct for unsigned negation
    b2.contains(intmask(-r_uint(n1)))

    # always check MININT
    if b1.contains(MININT):
        assert b2.contains(MININT)

    # check consistency with sub_bound
    b2viasub = IntBound.from_constant(0).sub_bound(b1)
    assert bound_eq(b2, b2viasub)

@given(ints)
def test_neg_const_random(t1):
    b1 = IntBound.from_constant(t1)
    r = b1.neg_bound()
    if t1 != -sys.maxint-1:
        assert r.is_constant()
        assert r.known_eq_const(-t1)


@given(knownbits_and_bound_with_contained_number, strategies.data())
def test_are_knownbits_implied(t, data):
    b, _ = t
    if b._are_knownbits_implied():
        n2 = data.draw(strategies.integers(b.lower, b.upper))
        assert b.contains(n2)


@given(knownbits_and_bound_with_contained_number)
def test_widen_then_intersect_random(t):
    b, n = t
    b1 = b.widen()
    assert b1._are_knownbits_implied()
    assert b1.contains(n)
    b2 = b1.clone()
    b2.intersect(b)
    assert bound_eq(b2, b)

@given(knownbits_and_bound_with_contained_number, ints, ints)
def test_is_within_range_random(t, x, y):
    b, n = t
    x, y = sorted([x, y])
    if b.is_within_range(x, y):
        assert x <= n <= y

@given(knownbits_and_bound_with_contained_number, knownbits_and_bound_with_contained_number)
def test_known_lt_gt_le_ge_random(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    if b1.known_lt(b2):
        assert n1 < n2
        assert b1.known_lt_const(n2)
        assert b2.known_gt(b1)
        assert b2.known_gt_const(n1)
    if b1.known_gt(b2):
        assert n1 > n2
        assert b1.known_gt_const(n2)
        assert b2.known_lt(b1)
        assert b2.known_lt_const(n1)
    if b1.known_le(b2):
        assert n1 <= n2
        assert b1.known_le_const(n2)
        assert b2.known_ge(b1)
        assert b2.known_ge_const(n1)
    if b1.known_ge(b2):
        assert n1 >= n2
        assert b1.known_ge_const(n2)
        assert b2.known_le(b1)
        assert b2.known_le_const(n1)

def test_known_lt_gt_le_ge_unsigned_example():
    b1 = IntBound.from_constant(10)
    b2 = IntBound.from_constant(100)
    assert b1.known_unsigned_lt(b2)

    b1 = IntBound.from_constant(10)
    b2 = IntBound.from_constant(10)
    assert b1.known_unsigned_le(b2)

    b1 = IntBound(0, 10)
    b2 = IntBound(128, 255)
    assert b1.known_unsigned_le(b2)

    b1 = IntBound(-510, -101)
    b2 = IntBound(-100, -10)
    assert b1.known_unsigned_le(b2)

    zero = IntBound.from_constant(0)
    unknown = IntBound.unbounded()
    assert zero.known_unsigned_le(unknown)

@given(knownbits_and_bound_with_contained_number, knownbits_and_bound_with_contained_number)
def test_known_lt_gt_le_ge_unsigned_random(t1, t2):
    b1, n1 = t1
    n1 = r_uint(n1)
    b2, n2 = t2
    n2 = r_uint(n2)
    if b1.known_unsigned_lt(b2):
        assert n1 < n2
        assert b2.known_unsigned_gt(b1)
    if b1.known_unsigned_gt(b2):
        assert n1 > n2
        assert b2.known_unsigned_lt(b1)
    if b1.known_unsigned_le(b2):
        assert n1 <= n2
        assert b2.known_unsigned_ge(b1)
    if b1.known_unsigned_ge(b2):
        assert n1 >= n2
        assert b2.known_unsigned_le(b1)

def test_known_ne_example():
    b1 = knownbits(0b000010,
                   0b111100)    # ????10
    b2 = knownbits(0b000001,
                   0b111100)    # ????01
    assert b1.known_ne(b2)

    b1 = IntBound(lower=0, upper=10)
    b2 = IntBound(lower=5, upper=10)
    assert not b1.known_ne(b2)

@given(knownbits_and_bound_with_contained_number, knownbits_and_bound_with_contained_number)
def test_known_ne_random(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    known_ne = b1.known_ne(b2)
    if known_ne:
        assert not b1.contains(n2)
        assert not b2.contains(n1)

@example((IntBound(-1, 0), 0),
         (IntBound.from_knownbits(r_uint(0b11100), r_uint(-0b1100000)), -100))
@given(knownbits_and_bound_with_contained_number, knownbits_and_bound_with_contained_number)
def test_known_ne_compatible_intersect_random(t1, t2):
    # check that intersect and known_ne are compatible
    b1, _ = t1
    b2, _ = t2
    known_ne = b1.known_ne(b2)
    try:
        b1.intersect(b2)
    except InvalidLoop:
        assert known_ne
    else:
        assert not known_ne

# --------------

def test_lowest_set_bit_only():
    n1 = r_uint(0b10001)
    r1 = lowest_set_bit_only(n1)
    assert r1 == r_uint(1)
    n2 = r_uint(0b00100)
    r2 = lowest_set_bit_only(n2)
    assert r2 == r_uint(4)
    n3 = r_uint(-1)
    r3 = lowest_set_bit_only(n3)
    assert r3 == r_uint(1)
    n4 = r_uint(0)
    r4 = lowest_set_bit_only(n4)
    assert r4 == r_uint(0)

def test_knownbits_intconst_examples():
    b1 = IntBound.from_constant(0b010010)
    assert b1.is_constant()
    assert b1.get_constant_int() == 0b010010
    assert b1.known_eq_const(0b010010)
    b2 = IntBound.from_constant(0b1)
    assert b2.is_constant()
    assert b2.get_constant_int() == 0b1
    assert b2.known_eq_const(0b1)
    b3 = IntBound.from_constant(0b0)
    assert b3.is_constant()
    assert b3.get_constant_int() == 0b0
    assert b3.known_eq_const(0b0)


def test_knownbits_minmax_nobounds_examples():
    # constant case
    b1 = IntBound.from_constant(42)
    assert b1._get_minimum_signed() == 42
    assert b1._get_maximum_signed() == 42
    # positive knownbits case
    b2 = knownbits(0b0110010,   # 11?01?
                   0b0001001)
    assert b2._get_minimum_signed() == 0b0110010
    assert not b2.contains(b2._get_minimum_signed() - 1)
    assert b2._get_maximum_signed() == 0b0111011
    assert not b2.contains(b2._get_maximum_signed() + 1)
    #negative knownbits_case
    b3 = knownbits(~0b0110010,  # 1...10?1101
                    0b0010000)
    assert b3._get_minimum_signed() == ~0b0110010
    assert not b3.contains(b3._get_minimum_signed() - 1)
    assert b3._get_maximum_signed() == ~0b0100010
    assert not b3.contains(b3._get_maximum_signed() + 1)

def test_knownbits_minmax_bounds_examples():
    # case (-Inf, 0]
    b1 = IntBound(lower=0,
                  tvalue=r_uint(5), tmask=r_uint(-8))   # ?...?101
    assert b1._get_minimum_signed() == 5
    assert b1._get_maximum_signed() == intmask((r_uint(5) | r_uint(-8)) & ~MININT)
    # case [0, Inf)
    b2 = IntBound(upper=0,
                  tvalue=r_uint(5), tmask=r_uint(-8))   # ?...?101
    assert b2._get_minimum_signed() == intmask(r_uint(5) | MININT)
    assert b2._get_maximum_signed() == -3

def test_knownbits_const_strings_examples():
    b1 = IntBound.from_constant(0b010010)
    assert check_knownbits_string(b1, "00010010", '0')
    b2 = IntBound.from_constant(0b1)
    assert check_knownbits_string(b2, "001", '0')
    b3 = IntBound.from_constant(0b0)
    assert check_knownbits_string(b3, "0", '0')
    b4 = IntBound.from_constant(-1)
    assert check_knownbits_string(b4, "1", '1')

def test_knownbits_unknowns_strings_examples():
    b1 = knownbits(0b010010,
                   0b001100)    # 01??10
    assert check_knownbits_string(b1, "01??10", '0')
    b2 = knownbits( 0b1010,
                   ~0b1011)     # ?...?1?10
    assert check_knownbits_string(b2, "1?10")

def test_knownbits_or_and_known_example():
    b1 = IntBound.unbounded()
    b2 = b1.or_bound(IntBound.from_constant(1))
    assert check_knownbits_string(b2, "1")
    b3 = b2.and_bound(IntBound.from_constant(1))
    assert b3.is_constant()
    assert b3.get_constant_int() == 1
    assert b3.known_eq_const(1)

def test_knownbits_or_and_unknown_example():
    b1 = IntBound.unbounded()
    assert not b1.is_constant()
    b2 = b1.or_bound(IntBound.from_constant(42))
    assert not b2.is_constant()
    b3 = b2.and_bound(IntBound.from_constant(-1))
    assert not b3.is_constant()

def test_knownbits_intersect_example():
    b1 = knownbits(0b10001010,
                   0b01110000)  # 1???1010
    b2 = knownbits(0b11000010,
                   0b00011100)  # 110???10
    b1.intersect(b2)
    assert b1.tvalue == r_uint(0b11001010)
    assert b1.tmask  == r_uint(0b00010000)   # 110?1010

def test_knownbits_intersect_disagree_examples():
    # b0 == b1
    # b0 and b2 disagree, b1 and b3 agree
    b0 = knownbits(0b001000,
                   0b110111)    # ??1???
    b2 = knownbits(0b000100,    #   !     <- disagreement
                   0b110011)    # ??01??
    b1 = knownbits(0b001000,
                   0b110111)    # ??1???
    b3 = knownbits(0b000000,
                   0b111111)    # ??????
    # expecting an exception
    with pytest.raises(Exception):
        b0.intersect(b2)
    # not expecting an exception
    b1.intersect(b3)

@example(t1=(IntBound.nonnegative(), 1), t2=(IntBound.unbounded(), 0))
@given(knownbits_and_bound_with_contained_number, knownbits_and_bound_with_contained_number)
def test_knownbits_intersect_random(t1, t2):
    b1, n1 = t1
    b = b1.clone()
    b2, n2 = t2
    try:
        changed = b.intersect(b2)
    except InvalidLoop:
        # the bounds were incompatible, so the examples can't be contained in
        # the other bound
        assert not b1.contains(n2)
        assert not b2.contains(n1)
    else:
        # the intersection worked. check that at least the lower and upper
        # bounds are in b1 and b2
        assert b1.contains(b._get_minimum_signed())
        assert b1.contains(b._get_maximum_signed())
        assert b2.contains(b._get_minimum_signed())
        assert b2.contains(b._get_maximum_signed())
        if b1.contains(n2):
            assert b.contains(n2)
        if b2.contains(n1):
            assert b.contains(n1)
        if changed:
            assert not bound_eq(b, b1)
        else:
            assert bound_eq(b, b1)

def test_get_minimum_signed_by_knownbits_above_full_range_bug():
    b1 = IntBound.from_constant(0)
    with pytest.raises(InvalidLoop):
        b1._get_maximum_signed_by_knownbits_atmost(-1)
    with pytest.raises(InvalidLoop):
        b1._get_minimum_signed_by_knownbits_atleast(1)

@given(knownbits_and_bound_with_contained_number, strategies.data())
def test_get_maximum_signed_by_knownbits_atmost_random(t1, data):
    b1, n1 = t1
    minimum = b1._get_minimum_signed_by_knownbits()
    threshold = data.draw(strategies.integers(minimum, MAXINT))
    new = b1._get_maximum_signed_by_knownbits_atmost(threshold)
    assert new <= threshold

@given(knownbits_and_bound_with_contained_number, strategies.data())
def test_get_minimum_signed_by_knownbits_atleast_random(t1, data):
    b1, n1 = t1
    maximum = b1._get_maximum_signed_by_knownbits_atmost()
    threshold = data.draw(strategies.integers(MININT, maximum))
    new = b1._get_minimum_signed_by_knownbits_atleast(threshold)
    assert new >= threshold

@given(knownbits_and_bound_with_contained_number, ints)
def test_get_maximum_signed_by_knownbits_atmost_full_range_random(t1, threshold):
    b1, n1 = t1
    try:
        new = b1._get_maximum_signed_by_knownbits_atmost(threshold)
    except InvalidLoop:
        assert threshold < n1
    else:
        assert new <= threshold

@given(knownbits_and_bound_with_contained_number, ints)
def test_get_minimum_signed_by_knownbits_atleast_full_range_random(t1, threshold):
    b1, n1 = t1
    try:
        new = b1._get_minimum_signed_by_knownbits_atleast(threshold)
    except InvalidLoop:
        assert threshold > n1
    else:
        assert new >= threshold

def test_validtnum_assertion_examples():
    # for each bit i: mask[i]==1 implies value[i]==0
    # the following tnum is invalid:
    with pytest.raises(AssertionError):
        b0 = knownbits(r_uint(0b111),
                       r_uint(0b010))
    # mask and value have to be r_uints
    with pytest.raises(AssertionError):
        b2 = IntBound.from_knownbits(0b101,
                               0b010)
    with pytest.raises(AssertionError):
        b3 = IntBound.from_knownbits(r_uint(0b101),
                               0b010)
    with pytest.raises(AssertionError):
        b4 = IntBound.from_knownbits(0b101,
                               r_uint(0b010))
    # this is valid:
    IntBound.from_knownbits(r_uint(0b101),
                            r_uint(0b010))

def test_widen_tnum():
    b = knownbits(0b10001010,
                  0b00110100)   # 10??1?10
    b.widen_update()
    assert b._are_knownbits_implied()

def test_shrink_bounds_by_knownbits():
    # positive case
    b1 = knownbits(0b101000,
                   0b000101)  # 101???
    assert b1.lower == 0b101000
    assert b1.upper == 0b101101
    # negative case
    b2 = knownbits(~0b010111,
                    0b000101)  # 1...101?0?
    assert b2.lower == ~0b010111
    assert b2.upper == ~0b010010

def test_shrink_knownbits_by_bounds():
    # constant positive case
    b1 = IntBound(lower=27, upper=27,
                  tvalue=r_uint(0),
                  tmask=r_uint(-1))
    assert b1.is_constant()
    assert b1.known_eq_const(27)
    # constant negative case
    b2 = IntBound(lower=-27, upper=-27,
                  tvalue=r_uint(0),
                  tmask=r_uint(-1))
    assert b2.is_constant()
    assert b2.known_eq_const(-27)
    # positive case
    b3 = IntBound(lower=49, upper=52,
                  tvalue=r_uint(0),
                  tmask=r_uint(-1))
    assert not b3.is_constant()
    assert check_knownbits_string(b3, "110???", '0')

def test_shrink_knownbits_by_bounds_invalid():
    b1 = IntBound(lower=0, upper=1,
                  tvalue=r_uint(0b10),
                  tmask=r_uint(~0b10), do_shrinking=False)
    with pytest.raises(InvalidLoop):
        b1._shrink_knownbits_by_bounds()
    

def test_intbound_repr():
    b = IntBound()
    assert repr(b) == 'IntBound.unbounded()'
    b = IntBound.nonnegative()
    assert repr(b) == 'IntBound.nonnegative()'
    b = IntBound(lower=0, upper=100)
    assert repr(b) == 'IntBound(0, 100)'
    b = IntBound().urshift_bound(IntBound.from_constant(10))
    assert repr(b) == 'IntBound(0, 0x3fffff%s)' % ('ffffffff' * (LONG_BIT == 64),)
    b = IntBound.from_constant(MININT)
    assert repr(b) == 'IntBound.from_constant(MININT)'
    b = IntBound.from_constant(-56)
    assert repr(b) == 'IntBound.from_constant(-56)'
    b = IntBound.from_knownbits(r_uint(0b0110), r_uint(0b1011), do_unmask=True)
    assert repr(b) == 'IntBound.from_knownbits(r_uint(0b100), r_uint(0b1011))'
    # generic case
    b = IntBound(5, 16, r_uint(0b0100), r_uint(0b1011))
    # XXX could be improved, the upper bound is not necessary
    assert repr(b) == 'IntBound(5, 15, r_uint(0b100), r_uint(0b1011))'

@given(knownbits_and_bound_with_contained_number)
def test_hypothesis_repr(t):
    b, _ = t
    s = repr(b)
    b2 = eval(s, {"IntBound": IntBound, "r_uint": r_uint,
                  "MININT": MININT, "MAXINT": MAXINT})
    assert bound_eq(b, b2)

@given(knownbits_and_bound_with_contained_number)
def test_hypothesis_is_constant_consistent(t):
    b, num = t
    b.is_constant() # run this for the asserts in is_constant

def test_intbound_str():
    b = IntBound()
    assert str(b) == '(?)'
    b = IntBound.nonnegative()
    assert str(b) == '(0 <= 0b0?...?)'
    b = IntBound(lower=0, upper=100)
    assert str(b) == '(0 <= 0b0...0??????? <= 100)'
    b = IntBound().urshift_bound(IntBound.from_constant(10))
    assert str(b) == '(0 <= 0b0000000000?...? <= 0x3fffff%s)' % ('ffffffff' * (LONG_BIT == 64),)
    b = IntBound(lower=0, upper=1230000000)
    if LONG_BIT == 64:
        assert str(b) == '(0 <= 0b0...0??????????????????????????????? <= 1230000000)'
    else:
        assert str(b) == '(0 <= 0b0?...? <= 1230000000)'
    b = IntBound(lower=0, upper=1230505081)
    if LONG_BIT == 64:
        assert str(b) == '(0 <= 0b0...0??????????????????????????????? <= 0x49580479)'
    else:
        assert str(b) == '(0 <= 0b0?...? = 0x49580479)'
    b = IntBound.from_constant(MININT)
    assert str(b) == '(MININT)'
    b = IntBound.from_constant(-56)
    assert str(b) == '(-56)'
    b = IntBound(0, 1)
    assert str(b) == '(bool)'
    b = IntBound(upper=MAXINT-16)
    assert str(b) == "(? <= MAXINT - 16)"
    b = IntBound(lower=MININT+16)
    assert str(b) == "(MININT + 16 <= ?)"

@given(knownbits_and_bound_with_contained_number)
def test_minmax_shrinking_random(t1):
    b0, n0 = t1
    assert not isinstance(n0, r_uint)
    b1 = IntBound(lower=b0.lower, upper=b0.upper,
                 tvalue=b0.tvalue, tmask=b0.tmask,
                 do_shrinking=True)
    assert b1.lower <= n0
    assert n0 <= b1.upper
    minimum = b1._get_minimum_signed()
    assert minimum >= b1.lower
    assert minimum <= n0
    assert b1.contains(minimum)
    maximum = b1._get_maximum_signed()
    assert maximum <= b1.upper
    assert maximum >= n0
    assert b1.contains(maximum)
    assert minimum <= maximum

@given(knownbits_and_bound_with_contained_number)
def test_minmax_noshrink_random(t1):
    b1, n1 = t1
    assert b1.lower <= n1
    assert n1 <= b1.upper
    minimum = b1._get_minimum_signed()
    assert minimum >= b1.lower
    assert minimum <= n1
    assert b1.contains(minimum)
    maximum = b1._get_maximum_signed()
    assert maximum <= b1.upper
    assert maximum >= n1
    assert b1.contains(maximum)
    assert minimum <= maximum


def test_knownbits_and():
    for _, _, b1 in some_bits():
        for _, _, b2 in some_bits():
            b3 = b1.and_bound(b2)
            for n1 in nnbr:
                for n2 in nbr:
                    if b1.contains(n1) and b2.contains(n2):
                        assert b3.contains(n1 & n2)

def test_knownbits_or():
    for _, _, b1 in some_bits():
        for _, _, b2 in some_bits():
            b3 = b1.or_bound(b2)
            for n1 in nnbr:
                for n2 in nbr:
                    if b1.contains(n1) and b2.contains(n2):
                        assert b3.contains(n1 | n2)

def test_knownbits_xor():
    for _, _, b1 in some_bits():
        for _, _, b2 in some_bits():
            b3 = b1.xor_bound(b2)
            for n1 in nnbr:
                for n2 in nbr:
                    if b1.contains(n1) and b2.contains(n2):
                        assert b3.contains(n1 ^ n2)

def test_knownbits_invert():
    for _, _, b1 in some_bits():
        b2 = b1.invert_bound()
        for n1 in nbr:
            if b1.contains(n1):
                assert b2.contains(~n1)
            else:
                assert not b2.contains(~n1)

def test_knownbits_neg():
    for _, _, b1 in some_bits():
        b2 = b1.neg_bound()
        for n1 in nbr:
            if b1.contains(n1):
                assert b2.contains(-n1)

def test_knownbits_add():
    for _, _, b1 in some_bits():
        for _, _, b2 in some_bits():
            b3 = b1.add_bound(b2)
            for n1 in nnbr:
                for n2 in nbr:
                    if b1.contains(n1) and b2.contains(n2):
                        assert b3.contains(n1 + n2)

def test_knownbits_sub():
    for _, _, b1 in some_bits():
        for _, _, b2 in some_bits():
            b3 = b1.sub_bound(b2)
            for n1 in nnbr:
                for n2 in nbr:
                    if b1.contains(n1) and b2.contains(n2):
                        assert b3.contains(n1 - n2)

def test_knownbits_lshift_examples():
    # both numbers constant case
    a1 = IntBound.from_constant(21)
    b1 = IntBound.from_constant(3)
    r1 = a1.lshift_bound(b1)
    assert a1.is_constant()
    assert (21 << 3) == r1.get_constant_int()
    assert 0 == (r1.get_constant_int() & 0b111)
    # knownbits case
    tv2 = 0b0100010     # 010??10
    tm2 = 0b0001100
    a2 = knownbits(tv2, tm2)
    b2 = IntBound.from_constant(3)
    r2 = a2.lshift_bound(b2)
    assert not r2.is_constant()
    assert r2.contains(tv2 << 3)
    assert r2.contains((tv2|tm2) << 3)
    assert check_knownbits_string(r2, "010??10000", '0')
    # complete shift out
    tv3 = 0b1001        # 1??1
    tm3 = 0b0110
    a3 = knownbits(tv3, tm3)
    b3 = IntBound.from_constant(LONG_BIT+1)
    r3 = a3.lshift_bound(b3)
    assert r3.is_constant()
    assert r3.get_constant_int() == 0

def test_knownbits_rshift_signed_consts_examples():
    # case 1a - both numbers constant positive case
    a1a = IntBound.from_constant(21)
    b1 = IntBound.from_constant(3)
    r1a = a1a.rshift_bound(b1)
    assert r1a.is_constant()
    assert (21 >> 3) == r1a.get_constant_int()
    # case 1b - both numbes constant negative case
    a1b = IntBound.from_constant(-21)
    r1b = a1b.rshift_bound(b1)
    assert r1b.is_constant()
    assert (-21 >> 3) == r1b.get_constant_int()

def test_knownbits_rshift_signed_partialunknowns_examples():
    # case 2a - knownbits case
    tv2a = 0b0100010     # 010??10
    tm2a = 0b0001100
    a2a = knownbits(tv2a, tm2a)
    b2 = IntBound.from_constant(3)
    r2a = a2a.rshift_bound(b2) # 010?
    assert not r2a.is_constant()
    assert r2a.contains(0b0100)
    assert r2a.contains(0b0101)
    # case 2b - knownbits case value sign extend
    tv2b = ~0b0101010   # 1...1?101?1
    tm2b =  0b0100010
    a2b = knownbits(tv2b, tm2b)
    r2b = a2b.rshift_bound(b2) # 1...1?10
    assert not r2b.is_constant()
    assert r2b.contains(~0b0101)
    assert r2b.contains(~0b0001)
    # case 2c - knownbits case mask sign extend
    tv2c = 0b0101010    # ?0...0101010
    tm2c = intmask(1 << (LONG_BIT-1))
    a2c = knownbits(tv2c, tm2c)
    r2c = a2c.rshift_bound(b2)  # ????0...0101
    assert not r2c.is_constant()
    assert r2c.contains(0b0101 | (tm2c>>3))
    assert r2c.contains(0b0101)

def test_knownbits_rshift_signed_completeshiftout_examples():
    #case 3a - complete shift out positive known
    tv3a = 0b1001        # 1??1
    tm3a = 0b0110
    a3a = knownbits(tv3a, tm3a)
    b3 = IntBound.from_constant(LONG_BIT+1)
    r3a = a3a.rshift_bound(b3)
    assert r3a.is_constant()
    assert r3a.get_constant_int() == 0
    # case 3b - complete shift out negative known (extend value sign)
    tv3b = ~0b1101      # 1...1?01?
    tm3b =  0b1001
    a3b = knownbits(tv3b, tm3b)
    r3b = a3b.rshift_bound(b3)
    assert r3b.is_constant()
    assert r3b.get_constant_int() == -1
    # case 3c - complete shift out unknown (extend mask sign)
    tv3c =  0b1000      # ?...?1??0
    tm3c = ~0b1001
    a3c = knownbits(tv3c, tm3c)
    r3c = a3c.rshift_bound(b3)
    assert not r3c.is_constant()
    assert r3c.contains(-1)

def test_knownbits_rshift_unsigned_consts_examples():
    # case 1a - both numbers constant positive case
    a1a = IntBound.from_constant(21)
    b1 = IntBound.from_constant(3)
    r1a = a1a.urshift_bound(b1)
    assert r1a.is_constant()
    assert intmask(r_uint(21) >> r_uint(3)) == r1a.get_constant_int()
    # case 1b - both numbes constant negative case
    a1b = IntBound.from_constant(-21)
    r1b = a1b.urshift_bound(b1)
    assert r1b.is_constant()
    assert intmask(r_uint(-21) >> r_uint(3)) == r1b.get_constant_int()

def test_knownbits_rshift_unsigned_partialunknowns_examples():
    # case 2a - knownbits case
    tv2a = 0b0100010     # 010??10
    tm2a = 0b0001100
    a2a = knownbits(tv2a, tm2a)
    b2 = IntBound.from_constant(3)
    r2a = a2a.urshift_bound(b2) # 010?
    assert not r2a.is_constant()
    assert r2a.contains(0b0100)
    assert r2a.contains(0b0101)
    # case 2b - knownbits case value sign extend
    tv2b = ~0b0101010   # 1...1?101?1
    tm2b =  0b0100010
    a2b = knownbits(tv2b, tm2b)
    r2b = a2b.urshift_bound(b2) # 0001...1?10
    assert not r2b.is_constant()
    assert r2b.contains(intmask(r_uint(~0b0001010) >> r_uint(3)))
    assert r2b.contains(intmask(r_uint(~0b0101010) >> r_uint(3)))
    # case 2c - knownbits case mask sign extend
    tv2c = 0b0101010    # ?0...0101010
    tm2c = intmask(1<<(LONG_BIT-1)) # 10...0
    a2c = knownbits(tv2c, tm2c)
    r2c = a2c.urshift_bound(b2)  # 0...0101
    assert not r2c.is_constant()
    assert r2c.contains(0b0101 | intmask(r_uint(tm2c)>>r_uint(3)))
    assert r2c.contains(0b0101)

def test_knownbits_rshift_unsigned_completeshiftout_examples():
    # case 3a - complete shift out positive known
    tv3a = 0b1001        # 1??1
    tm3a = 0b0110
    a3a = knownbits(tv3a, tm3a)
    b3 = IntBound.from_constant(LONG_BIT+1)
    r3a = a3a.urshift_bound(b3) # 0
    assert r3a.is_constant()
    assert r3a.get_constant_int() == 0
    # case 3b - complete shift out negative known (extend value sign)
    tv3b = ~0b1101      # 1...1?01?
    tm3b =  0b1001
    a3b = knownbits(tv3b, tm3b)
    r3b = a3b.urshift_bound(b3) # 0
    assert r3b.is_constant()
    assert r3b.get_constant_int() == 0
    # case 3c - complete shift out unknown (extend mask sign)
    tv3c =  0b1000      # ?...?1??0
    tm3c = ~0b1001
    a3c = knownbits(tv3c, tm3c)
    r3c = a3c.urshift_bound(b3) # 0
    assert r3c.is_constant()
    assert r3c.known_eq_const(0)

def test_knownbits_add_concrete_example():
    a1 = knownbits(             # 10??10 = {34,38,42,46}
            0b100010,           # +   11
            0b001100)           #  ??1
    b1 = 3                      # ------
    r1 = a1.add(b1)             # 1???01 = {33,37,41,45,49,53,57,61}
    # bounds of a1 == [34, 46]; bounds of r1 == [37; 49]
    assert not r1.is_constant()
    #assert r1.contains(0b100001)    # not true because bounds
    assert r1.contains(0b100101)
    assert r1.contains(0b101001)
    assert r1.contains(0b101101)
    assert r1.contains(0b110001)
    #assert r1.contains(0b110101)    # not true because bounds
    #assert r1.contains(0b111001)    # not true because bounds
    #assert r1.contains(0b111101)    # not true because bounds
    assert not r1.contains(0b111111)
    assert not r1.contains(0b1111101)

def test_knownbits_sub_concrete_example():
    a1 = knownbits(             # 10??01 = {33,37,41,45}
            0b100001,           # -   11
            0b001100)           # ???1
    b1 = 3                      # ------
    r1 = a1.add(intmask(-b1))   # ????10 = {34,38,42,46,...}
    # bounds of a1 == [33, 45]; bounds of r1 == [30; 42]
    assert not r1.is_constant()
    assert r1.contains(0b011110)
    assert r1.contains(0b100010)
    assert r1.contains(0b100110)
    assert r1.contains(0b101010)

def test_knownbits_and_backwards_otherconst_examples():
    r = IntBound.from_constant(0b11).and_bound_backwards(IntBound.from_constant(0b00))
    assert check_knownbits_string(r, "??00")
    r = IntBound.from_constant(0b11).and_bound_backwards(IntBound.from_constant(0b11))
    assert check_knownbits_string(r, "??11")
    x = knownbits( 0b10000,     # ?...?10???
                  ~0b11000)
    r = x.and_bound_backwards(IntBound.from_constant(0))
    assert check_knownbits_string(r, "??0????")
    x = knownbits( 0b1010,      # ?...?1010
                  ~0b1111)
    r = x.and_bound_backwards(IntBound.from_constant(0))
    assert check_knownbits_string(r, "??0?0?")
    r = IntBound.from_constant(0b11).and_bound_backwards(IntBound.from_constant(0b10))
    assert check_knownbits_string(r, "??10")
    r = IntBound.from_constant(0b111).and_bound_backwards(IntBound.from_knownbits(r_uint(0b100), ~r_uint(0b110)))
    assert check_knownbits_string(r, "?10?")
    x = IntBound.unbounded()
    o = knownbits(0b101010,
                  0b010100) # 1?1?10
    r = o.and_bound_backwards(IntBound.from_constant(0b110))
    assert check_knownbits_string(r, "0?011?")

def test_knownbits_and_backwards_example():
    o = knownbits(0b11100000,
                  0b00000111) # 11100???
    r = knownbits(0b10000100,
                  0b00101001) # 10?0?10?
    s = o.and_bound_backwards(r)
    assert check_knownbits_string(s, '?10???1??', '?')

def test_knownbits_and_backwards_example_inconsistent():
    o = knownbits(0b111000000, 0b000000111) # 111000???
    r = knownbits(0b100100100, 0b001001001) # 10?10?10?
    with pytest.raises(InvalidLoop):
        o.and_bound_backwards(r)

def test_knownbits_or_backwards_example():
    o = knownbits(0b11000000,
                  0b00000111) # 11000???
    r = knownbits(0b10100100,
                  0b01001001) # 1?10?10?
    s = o.or_bound_backwards(r)
    assert check_knownbits_string(s, '00??10??0?', '0')

    o = knownbits(0b111000000, 0b000000111) # 111000???
    r = knownbits(0b100100100, 0b001001001) # 10?10?10?
    with pytest.raises(InvalidLoop):
        s = o.or_bound_backwards(r)

def test_knownbits_rshift_backwards_example():
    o = IntBound.from_constant(3)
    x1 = IntBound.unbounded()
    r1 = knownbits(0b101010,
                   0b010100) # 1?1?10
    res1 = r1.rshift_bound_backwards(o)
    assert check_knownbits_string(res1, "1?1?10???", '0')
    r2 = knownbits(0b101010,
                   0b010100) # 1?1?10
    x3 = IntBound.unbounded()
    r3 = IntBound.from_constant(1)
    res3 = r3.rshift_bound_backwards(o)
    assert not res3.is_constant()
    assert check_knownbits_string(res3, "1???", '0')

def test_knownbits_lshift_backwards_example():
    o = IntBound.from_constant(3)
    r1 = knownbits(0b101000,
                   0b010000) # 1?1000
    res1 = r1.lshift_bound_backwards(o)
    assert not res1.is_constant()
    assert res1.knownbits_string().startswith("???") \
        and res1.knownbits_string().endswith("001?1")
    r2 = knownbits(0b100000,
                   0b011000) # 1??000
    res2 = r2.lshift_bound_backwards(o)
    assert res2.knownbits_string().endswith("1??")
    assert res2.knownbits_string().startswith("???0")
    r3 = knownbits(MININT, 0) # 1
    res3 = r3.lshift_bound_backwards(o)
    assert not res3.is_constant()
    assert res3.knownbits_string().startswith("???1")

def test_knownbits_lshift_backwards_example_inconsistent():
    o = IntBound.from_constant(3)
    r1 = knownbits(0b101001,
                   0b010000) # 1?1000
    with pytest.raises(InvalidLoop):
        r1.lshift_bound_backwards(o)

@given(knownbits_and_bound_with_contained_number, shift_amount)
def test_knownbits_lshift_backwards_random(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    result = b1.lshift_bound(b2)
    try:
        r = ovfcheck(n1 << n2)
    except OverflowError:
        assume(False)
    orig = result.lshift_bound_backwards(b2)
    assert orig.contains(n1)
    b1.intersect(orig) # this must not fail


@given(constant, constant)
def test_const_stays_const_or(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    r = b1.or_bound(b2)
    assert r.is_constant()
    assert r.known_eq_const(n1 | n2)
    assert r.get_constant_int() == n1 | n2

@given(constant, constant)
def test_const_stays_const_and(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    r = b1.and_bound(b2)
    assert r.is_constant()
    assert r.known_eq_const(n1 & n2)
    assert r.get_constant_int() == n1 & n2

@given(constant, constant)
def test_const_stays_const_xor(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    r = b1.xor_bound(b2)
    assert r.is_constant()
    assert r.known_eq_const(n1 ^ n2)
    assert r.get_constant_int() == n1 ^ n2

@given(constant)
def test_const_stays_const_invert(t1):
    b1, n1 = t1
    r = b1.invert_bound()
    assert r.is_constant()
    assert r.known_eq_const(~n1)
    assert r.get_constant_int() == ~n1

@given(constant, constant)
def test_const_stays_const_lshift(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    r = b1.lshift_bound(b2)
    if n2 >= LONG_BIT:
        assert r.is_constant()
        assert r.known_eq_const(0)
    elif n2 >= 0:
        assert r.is_constant()
        assert r.known_eq_const(intmask(n1 << n2))

@given(constant, constant)
def test_const_stays_const_urshift(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    r = b1.urshift_bound(b2)
    if n2 >= LONG_BIT:
        assert r.is_constant()
        assert r.known_eq_const(0)
    elif n2 >= 0:
        assert r.is_constant()
        assert r.known_eq_const(intmask(r_uint(n1) >> r_uint(n2)))

@given(constant, constant)
def test_const_stays_const_rshift(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    r = b1.rshift_bound(b2)
    if n2 >= LONG_BIT:
        assert r.is_constant()
        if n1 < 0:
            assert r.known_eq_const(-1)
        else:
            assert r.known_eq_const(0)
    elif n2 >= 0:
        assert r.is_constant()
        assert r.known_eq_const(intmask(n1) >> intmask(n2))

@given(maybe_valid_value_mask_pair)
def test_validtnum_assertion_random(t1):
    # this one does both positive and negative examples
    val, msk = t1
    is_valid = (0 == val & msk)
    if is_valid:
        b = knownbits(val, msk)
    else:
        with pytest.raises(AssertionError):
            b = knownbits(val, msk)

@given(knownbits_and_bound_with_contained_number, strategies.integers(-5, LONG_BIT + 10), strategies.integers(0, LONG_BIT + 10), strategies.integers(0, LONG_BIT + 10))
def test_rshift_signed_random(t1, a, b, c):
    b1, n1 = t1
    a, n2, c = sorted([a, b, c])
    b2 = IntBound(a, c)
    r = b1.rshift_bound(b2)
    print b1, b2, r, n1, n2, n1 >> n2
    assert r.contains(n1 >> n2)

@given(knownbits_and_bound_with_contained_number, strategies.integers(-5, LONG_BIT + 10), strategies.integers(0, LONG_BIT + 10), strategies.integers(0, LONG_BIT + 10))
def test_rshift_unsigned_random(t1, a, b, c):
    b1, n1 = t1
    a, n2, c = sorted([a, b, c])
    b2 = IntBound(a, c)
    r = b1.urshift_bound(b2)
    assert r.contains(intmask(r_uint(n1) >> r_uint(n2)))
    if n1 < 0 and n2 > 0 and r.is_constant():
        assert r.get_constant_int() >= 0


@given(knownbits_and_bound_with_contained_number, pos_relatively_small_values)
def test_rshift_signed_const_random(t1, n2):
    b1, n1 = t1
    b2 = IntBound.from_constant(n2)
    r = b1.rshift_bound(b2)
    assert r.contains(n1 >> n2)

@given(knownbits_and_bound_with_contained_number, pos_relatively_small_values)
def test_rshift_unsigned_const_random(t1, n2):
    b1, n1 = t1
    b2 = IntBound.from_constant(n2)
    r = b1.urshift_bound(b2)
    assert r.contains(intmask(r_uint(n1) >> r_uint(n2)))
    if n1 < 0 and n2 > 0 and r.is_constant():
        assert r.get_constant_int() >= 0

@given(knownbits_and_bound_with_contained_number, knownbits_and_bound_with_contained_number)
def test_knownbits_and_backwards_random(t1, t2):
    b1, n1 = t1     # self
    b2, n2 = t2     # other
    rb = b1.and_bound(b2)
    rn = n1 & n2
    newb1 = b2.and_bound_backwards(rb)
    assert newb1.contains(n1)
    # this should not fail
    b1.intersect(newb1)

@given(knownbits_and_bound_with_contained_number, knownbits_and_bound_with_contained_number)
def test_knownbits_or_backwards_random(t1, t2):
    b1, n1 = t1     # self
    b2, n2 = t2     # other
    rb = b1.or_bound(b2)
    rn = n1 & n2
    newb1 = b2.or_bound_backwards(rb)
    assert newb1.contains(n1)
    # this should not fail
    b1.intersect(newb1)

@given(knownbits_and_bound_with_contained_number, constant)
def test_knownbits_urshift_backwards_random(t1, t2):
    b1, n1 = t1     # self
    b2, n2 = t2     # other
    rb = b1.urshift_bound(b2)
    newb1 = rb.urshift_bound_backwards(b2)
    assert newb1.contains(n1)
    # this should not fail
    b1.intersect(newb1)

@given(knownbits_and_bound_with_contained_number, constant)
def test_knownbits_rshift_backwards_random(t1, t2):
    b1, n1 = t1     # self
    b2, n2 = t2     # other
    rb = b1.rshift_bound(b2)
    newb1 = rb.rshift_bound_backwards(b2)
    assert newb1.contains(n1)
    # this should not fail
    b1.intersect(newb1)

def test_knownbits_div_bug():
    b1 = IntBound.unbounded()
    b2 = knownbits(0b1, r_uint(-2))  # ?????1
    r = b1.py_div_bound(b2)
    assert r.lower == MININT and r.upper == MAXINT

def knownbits(tvalue, tmask=0, do_unmask=False):
    if not isinstance(tvalue, r_uint):
        tvalue = r_uint(tvalue)
    if not isinstance(tmask, r_uint):
        tmask = r_uint(tmask)
    return IntBound.from_knownbits(tvalue, tmask, do_unmask)

def check_knownbits_string(r, lower_bits, upper_fill='?'):
    return r.knownbits_string() == upper_fill*(LONG_BIT-len(lower_bits)) + lower_bits

def test_getnullness_examples():
    b = IntBound(10, 1000)
    assert b.getnullness() == INFO_NONNULL
    b = IntBound.from_constant(0)
    assert b.getnullness() == INFO_NULL
    b = IntBound(-10000, -10)
    assert b.getnullness() == INFO_NONNULL
    b = IntBound.from_knownbits(r_uint(0b1), ~r_uint(0b1))
    assert b.getnullness() == INFO_NONNULL

@given(knownbits_and_bound_with_contained_number)
def test_getnullness_random(t1):
    b1, n1 = t1
    res = b1.getnullness()
    if res == INFO_NONNULL:
        assert n1 != 0
    elif res == INFO_NULL:
        assert n1 == 0
    else:
        assert res == INFO_UNKNOWN

@given(knownbits_and_bound_with_contained_number)
def test_make_bool(t1):
    b1, n1 = t1
    if b1.contains(0) or b1.contains(1):
        b1.make_bool()
        assert b1.is_bool()

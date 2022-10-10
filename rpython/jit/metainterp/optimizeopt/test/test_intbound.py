from rpython.jit.metainterp.optimizeopt.intutils import IntBound, IntUpperBound, \
     IntLowerBound, IntUnbounded, ConstIntBound, IntBoundKnownbits, next_pow2_m1, \
     IntLowerUpperBound, msbonly, MININT, MAXINT

from copy import copy
import sys
from rpython.rlib.rarithmetic import LONG_BIT, ovfcheck, r_uint, intmask

from hypothesis import given, strategies, example

import pytest

special_values_set = (
    range(-100, 100) +
    [2 ** i for i in range(1, LONG_BIT)] +
    [-2 ** i for i in range(1, LONG_BIT)] +
    [2 ** i - 1 for i in range(1, LONG_BIT)] +
    [-2 ** i - 1 for i in range(1, LONG_BIT)] +
    [2 ** i + 1 for i in range(1, LONG_BIT)] +
    [-2 ** i + 1 for i in range(1, LONG_BIT)] +
    [sys.maxint, -sys.maxint-1])

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


def bound(a, b):
    if a is None and b is None:
        return IntUnbounded()
    elif a is None:
        return IntUpperBound(b)
    elif b is None:
        return IntLowerBound(a)
    else:
        return IntLowerUpperBound(a, b)

def const(a):
    return ConstIntBound(a)


def build_bound_with_contained_number(a, b, c):
    a, b, c = sorted([a, b, c])
    r = bound(a, c)
    assert r.contains(b)
    return r, b

def build_some_bits_known(a, b):
    return knownbits(a&~b, b), a

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

bound_with_contained_number = strategies.one_of(
    unbounded, lower_bounded, upper_bounded, constant, bounded)

knownbits_with_contained_number = strategies.one_of(
    constant, some_bits_known, unbounded)

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
            elif n in border:
                assert b.contains(n)
                if n == upper:
                    assert b.known_le(const(upper))
                else:
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
            lt = IntUnbounded()
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

            gt = IntUnbounded()
            gt.make_gt(b1)
            gt.make_gt(b2)
            for n in nbr:
                c = const(n)
                if b1.known_ge(c) or b2.known_ge(c):
                    assert gt.known_gt(c)
                else:
                    assert not gt.known_gt(c)
            assert not gt.known_lt(c)
            assert not gt.known_le(c)

            le = IntUnbounded()
            le.make_le(b1)
            le.make_le(b2)
            for n in nbr:
                c = const(n)
                if b1.known_le(c) or b2.known_le(c):
                    assert le.known_le(c)
                else:
                    assert not le.known_le(c)
                assert not le.known_gt(c)
                assert not le.known_ge(c)


            ge = IntUnbounded()
            ge.make_ge(b1)
            ge.make_ge(b2)
            for n in nbr:
                c = const(n)
                if b1.known_ge(c) or b2.known_ge(c):
                    assert ge.known_ge(c)
                else:
                    assert not ge.known_ge(c)
                assert not ge.known_lt(c)
                assert not ge.known_le(c)

            gl = IntUnbounded()
            gl.make_ge(b1)
            gl.make_le(b2)
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

def test_intersect():
    for _, _, b1 in some_bounds():
        for _, _, b2 in some_bounds():
            b = copy(b1)
            b.intersect(b2)
            for n in nbr:
                if b1.contains(n) and b2.contains(n):
                    assert b.contains(n)
                else:
                    assert not b.contains(n)

def test_add():
    for _, _, b1 in some_bounds():
        for n1 in nbr:
            b2 = b1.add(n1)
            for n2 in nbr:
                c1 = const(n2)
                c2 = const(n2 + n1)

                if b1.known_le(c1):
                    assert b2.known_le(c2)
                else:
                    assert not b2.known_le(c2)

                if b1.known_ge(c1):
                    assert b2.known_ge(c2)
                else:
                    assert not b2.known_ge(c2)

                if b1.known_le(c1):
                    assert b2.known_le(c2)
                else:
                    assert not b2.known_lt(c2)

                if b1.known_lt(c1):
                    assert b2.known_lt(c2)
                else:
                    assert not b2.known_lt(c2)

                if b1.known_gt(c1):
                    assert b2.known_gt(c2)
                else:
                    assert not b2.known_gt(c2)

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

    a=bound(-3, 2).mul(-1)
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
    b10 = IntLowerUpperBound(0, 10)
    b100 = IntLowerUpperBound(0, 100)
    bmax = IntLowerUpperBound(0, sys.maxint/2)
    assert not b10.lshift_bound(b100).has_upper
    assert not bmax.lshift_bound(b10).has_upper
    assert b10.lshift_bound(b10).has_upper

    for b in (b10, b100, bmax, IntLowerUpperBound(0, 0)):
        for shift_count_bound in (IntLowerUpperBound(7, LONG_BIT), IntLowerUpperBound(-7, 7)):
            #assert not b.lshift_bound(shift_count_bound).has_upper
            assert not b.rshift_bound(shift_count_bound).has_upper


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

def test_and_bound():
    for _, _, b1 in some_bounds():
        for _, _, b2 in some_bounds():
            b3 = b1.and_bound(b2)
            for n1 in nbr:
                for n2 in nbr:
                    if b1.contains(n1) and b2.contains(n2):
                        assert b3.contains(n1 & n2)

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
    assert next_pow2_m1(0) == 0
    assert next_pow2_m1(1) == 1
    assert next_pow2_m1(7) == 7
    assert next_pow2_m1(256) == 511
    assert next_pow2_m1(255) == 255
    assert next_pow2_m1(80) == 127
    assert next_pow2_m1((1 << 32) - 5) == (1 << 32) - 1
    assert next_pow2_m1((1 << 64) - 1) == (1 << 64) - 1

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

@given(bound_with_contained_number, bound_with_contained_number)
def test_make_random(t1, t2):
    def d(b):
        return b.has_lower, b.lower, b.has_upper, b.upper
    b1, n1 = t1
    b2, n2 = t2

    for meth in [IntBound.make_le, IntBound.make_lt, IntBound.make_ge, IntBound.make_gt]:
        b = b1.clone()
        meth(b, b2)
        data = d(b)
        assert not meth(b, b2)
        assert data == d(b) # idempotent


@given(bound_with_contained_number, bound_with_contained_number)
def test_add_bound_random(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    print b1, n1
    print b2, n2
    b3 = b1.add_bound(b2)
    try:
        r = ovfcheck(n1 + n2)
    except OverflowError:
        assert not b3.is_bounded()
    else:
        assert b3.contains(r)

@given(bound_with_contained_number, bound_with_contained_number)
def test_sub_bound_random(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    print b1, n1
    print b2, n2
    b3 = b1.sub_bound(b2)
    try:
        r = ovfcheck(n1 - n2)
    except OverflowError:
        assert not b3.is_bounded()
    else:
        assert b3.contains(r)

@given(bound_with_contained_number, bound_with_contained_number)
def test_mul_bound_random(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    b3 = b1.mul_bound(b2)
    try:
        r = ovfcheck(n1 * n2)
    except OverflowError:
        assert not b3.is_bounded()
    else:
        assert b3.contains(r)

@given(bound_with_contained_number, bound_with_contained_number)
def test_div_bound_random(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    b3 = b1.py_div_bound(b2)
    if n1 == -sys.maxint-1 and n2 == -1:
        return # overflow
    if n2 != 0:
        assert b3.contains(n1 / n2)   # Python-style div

@given(bound_with_contained_number, bound_with_contained_number)
def test_mod_bound_random(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    b3 = b1.mod_bound(b2)
    if n1 == -sys.maxint-1 and n2 == -1:
        return # overflow
    if n2 != 0:
        assert b3.contains(n1 % n2)   # Python-style mod

@given(bound_with_contained_number, bound_with_contained_number)
def test_and_bound_random(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    b3 = b1.and_bound(b2)
    r = n1 & n2
    assert b3.contains(r)

@given(bound_with_contained_number, bound_with_contained_number)
def test_or_bound_random(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    b3 = b1.or_bound(b2)
    r = n1 | n2
    assert b3.contains(r)

@given(bound_with_contained_number, bound_with_contained_number)
def test_xor_bound_random(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    b3 = b1.xor_bound(b2)
    r = n1 ^ n2
    assert b3.contains(r)

@given(bound_with_contained_number)
def test_invert_bound_random(t1):
    b1, n1 = t1
    b2 = b1.invert_bound()
    assert b2.contains(~n1)

@given(bound_with_contained_number)
@example((IntUpperBound(-100), -sys.maxint-1))
@example((ConstIntBound(-sys.maxint - 1), -sys.maxint-1))
@example((IntLowerUpperBound(-sys.maxint - 1, -sys.maxint+10), -sys.maxint-1))
def test_neg_bound_random(t1):
    b1, n1 = t1
    b2 = b1.neg_bound()
    if n1 != -sys.maxint - 1:
        assert b2.contains(intmask(-n1))
    else:
        assert not b2.has_upper

# --------------


def test_knownbits_intconst_examples():
    b1 = ConstIntBound(0b010010)
    assert b1.is_constant()
    assert b1.get_constant_int() == 0b010010
    assert b1.equals(0b010010)
    b2 = ConstIntBound(0b1)
    assert b2.is_constant()
    assert b2.get_constant_int() == 0b1
    assert b2.equals(0b1)
    b3 = ConstIntBound(0b0)
    assert b3.is_constant()
    assert b3.get_constant_int() == 0b0
    assert b3.equals(0b0)

def test_knownbits_minmax_nobounds_examples():
    # constant case
    b1 = ConstIntBound(42)
    assert b1.get_minimum() == 42
    assert b1.get_maximum() == 42
    # positive knownbits case
    b2 = knownbits(0b0110010,   # 11?01?
                   0b0001001)
    assert b2.get_minimum() == 0b0110010
    assert not b2.contains(b2.get_minimum() - 1)
    assert b2.get_maximum() == 0b0111011
    assert not b2.contains(b2.get_maximum() + 1)
    #negative knownbits_case
    b3 = knownbits(~0b0110010,  # 1...10?1101
                    0b0010000)
    assert b3.get_minimum() == ~0b0110010
    assert not b3.contains(b3.get_minimum() - 1)
    assert b3.get_maximum() == ~0b0100010
    assert not b3.contains(b3.get_maximum() + 1)

def test_knownbits_minmax_bounds_examples():
    # case (-Inf, 0]
    b1 = IntBound(lower=0, has_lower=True,
                  tvalue=u(5), tmask=u(-8))   # ?...?101
    assert b1.get_minimum() == 0
    assert b1.get_maximum() == intmask((u(5) | u(-8)) & ~(1<<(LONG_BIT-1)))
    # case [0, Inf)
    b2 = IntBound(upper=0, has_upper=True,
                  tvalue=u(5), tmask=u(-8))   # ?...?101
    assert b2.get_minimum() == intmask(u(5) | (1<<(LONG_BIT-1)))
    assert b2.get_maximum() == 0

def test_knownbits_const_strings_examples():
    b1 = ConstIntBound(0b010010)
    assert check_knownbits_string(b1, "00010010", '0')
    b2 = ConstIntBound(0b1)
    assert check_knownbits_string(b2, "001", '0')
    b3 = ConstIntBound(0b0)
    assert check_knownbits_string(b3, "0", '0')
    b4 = ConstIntBound(-1)
    assert check_knownbits_string(b4, "1", '1')

def test_knownbits_unknowns_strings_examples():
    b1 = knownbits(0b010010,
                   0b001100)    # 01??10
    assert check_knownbits_string(b1, "01??10", '0')
    b2 = knownbits( 0b1010,
                   ~0b1011)     # ?...?1?10
    assert check_knownbits_string(b2, "1?10")

def test_knownbits_or_and_known_example():
    b1 = IntUnbounded()
    b2 = b1.or_bound(ConstIntBound(1))
    assert check_knownbits_string(b2, "1")
    b3 = b2.and_bound(ConstIntBound(1))
    assert b3.is_constant()
    assert b3.get_constant_int() == 1
    assert b3.equals(1)

def test_knownbits_or_and_unknown_example():
    b1 = IntUnbounded()
    assert not b1.is_constant()
    b2 = b1.or_bound(ConstIntBound(42))
    assert not b2.is_constant()
    b3 = b2.and_bound(ConstIntBound(-1))
    assert not b3.is_constant()

def test_knownbits_intersect_example():
    b1 = knownbits(0b10001010,
                   0b01110000)  # 1???1010
    b2 = knownbits(0b11000010,
                   0b00011100)  # 110???10
    b1.intersect(b2)
    assert b1.tvalue == u(0b11001010)
    assert b1.tmask  == u(0b00010000)   # 110?1010

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

def test_knownbits_contains_examples():
    bA = knownbits(0b001000,
                   0b110111)    # ??1???
    b1 = knownbits(0b000000,
                   0b111111)    # ??????
    assert b1.contains(bA)
    assert ~bA.contains(b1)
    bB = knownbits(0b101000,
                   0b000010)    # 1010?0
    b2 = knownbits(0b101010,    #     !! <- no subset
                   0b000001)    # 10101?
    assert ~bB.contains(b2)
    assert ~b2.contains(bB)

def test_validtnum_assertion_examples():
    # for each bit i: mask[i]==1 implies value[i]==0
    # the following tnum is invalid:
    with pytest.raises(Exception):
        b0 = IntBoundKnownbits(u(0b111),
                               u(0b010))
    # mask and value have to be r_uints
    with pytest.raises(Exception):
        b2 = IntBoundKnownbits(0b101,
                               0b010)
    with pytest.raises(Exception):
        b3 = IntBoundKnownbits(u(0b101),
                               0b010)
    with pytest.raises(Exception):
        b4 = IntBoundKnownbits(0b101,
                               u(0b010))
    # this is valid:
    b1 = IntBoundKnownbits(u(0b101),
                           u(0b010))

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
    a1 = ConstIntBound(21)
    b1 = ConstIntBound(3)
    r1 = a1.lshift_bound(b1)
    assert a1.is_constant()
    assert (21 << 3) == r1.get_constant_int()
    assert 0 == (r1.get_constant_int() & 0b111)
    # knownbits case
    tv2 = 0b0100010     # 010??10
    tm2 = 0b0001100
    a2 = knownbits(tv2, tm2)
    b2 = ConstIntBound(3)
    r2 = a2.lshift_bound(b2)
    assert not r2.is_constant()
    assert r2.contains(tv2 << 3)
    assert r2.contains((tv2|tm2) << 3)
    assert check_knownbits_string(r2, "010??10000", '0')
    # complete shift out
    tv3 = 0b1001        # 1??1
    tm3 = 0b0110
    a3 = knownbits(tv3, tm3)
    b3 = ConstIntBound(LONG_BIT+1)
    r3 = a3.lshift_bound(b3)
    assert r3.is_constant()
    assert r3.get_constant_int() == 0

def test_knownbits_rshift_signed_consts_examples():
    # case 1a - both numbers constant positive case
    a1a = ConstIntBound(21)
    b1 = ConstIntBound(3)
    r1a = a1a.rshift_bound(b1)
    assert r1a.is_constant()
    assert (21 >> 3) == r1a.get_constant_int()
    # case 1b - both numbes constant negative case
    a1b = ConstIntBound(-21)
    r1b = a1b.rshift_bound(b1)
    assert r1b.is_constant()
    assert (-21 >> 3) == r1b.get_constant_int()

def test_knownbits_rshift_signed_partialunknowns_examples():
    # case 2a - knownbits case
    tv2a = 0b0100010     # 010??10
    tm2a = 0b0001100
    a2a = knownbits(tv2a, tm2a)
    b2 = ConstIntBound(3)
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
    b3 = ConstIntBound(LONG_BIT+1)
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
    a1a = ConstIntBound(21)
    b1 = ConstIntBound(3)
    r1a = a1a.urshift_bound(b1)
    assert r1a.is_constant()
    assert intmask(u(21) >> u(3)) == r1a.get_constant_int()
    # case 1b - both numbes constant negative case
    a1b = ConstIntBound(-21)
    r1b = a1b.urshift_bound(b1)
    assert r1b.is_constant()
    assert intmask(u(-21) >> u(3)) == r1b.get_constant_int()

def test_knownbits_rshift_unsigned_partialunknowns_examples():
    # case 2a - knownbits case
    tv2a = 0b0100010     # 010??10
    tm2a = 0b0001100
    a2a = knownbits(tv2a, tm2a)
    b2 = ConstIntBound(3)
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
    assert r2b.contains(intmask(u(~0b0001010) >> u(3)))
    assert r2b.contains(intmask(u(~0b0101010) >> u(3)))
    # case 2c - knownbits case mask sign extend
    tv2c = 0b0101010    # ?0...0101010
    tm2c = intmask(1<<(LONG_BIT-1)) # 10...0
    a2c = knownbits(tv2c, tm2c)
    r2c = a2c.urshift_bound(b2)  # 0...0101
    assert not r2c.is_constant()
    assert r2c.contains(0b0101 | intmask(u(tm2c)>>u(3)))
    assert r2c.contains(0b0101)

def test_knownbits_rshift_unsigned_completeshiftout_examples():
    # case 3a - complete shift out positive known
    tv3a = 0b1001        # 1??1
    tm3a = 0b0110
    a3a = knownbits(tv3a, tm3a)
    b3 = ConstIntBound(LONG_BIT+1)
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
    assert r3c.equals(0)

def test_knownbits_add_concrete_example():
    a1 = knownbits(             # 10??10 = {34,38,42,46}
            0b100010,           # +   11
            0b001100)           #  ??1
    b1 = 3                      # ------
    r1 = a1.add(b1)             # 1???01 = {33,37,41,45,49,53,57,61}
    assert not r1.is_constant()
    assert r1.contains(0b100001)
    assert r1.contains(0b100101)
    assert r1.contains(0b101001)
    assert r1.contains(0b101101)
    assert r1.contains(0b110001)
    assert r1.contains(0b110101)
    assert r1.contains(0b111001)
    assert r1.contains(0b111101)
    assert not r1.contains(0b111111)
    assert not r1.contains(0b1111101)

def test_knownbits_sub_concrete_example():
    a1 = knownbits(             # 10??01 = {33,37,41,45}
            0b100001,           # -   11
            0b001100)           # ???1
    b1 = 3                      # ------
    r1 = a1.add(intmask(-b1))   # ????10 = {34,38,42,46,...}
    assert not r1.is_constant()
    assert r1.contains(0b100010)
    assert r1.contains(0b000110)
    assert r1.contains(0b101010)
    assert r1.contains(0b001110)
    assert r1.contains(0b110010)
    assert r1.contains(0b010110)
    assert r1.contains(0b111010)
    assert r1.contains(0b011110)

def test_knownbits_int_and_backwards_otherconst_examples():
    x = IntUnbounded()          # ?...?
    r = x.int_and_backwards(ConstIntBound(0b11), 0)
    assert check_knownbits_string(r, "??00")
    r = x.int_and_backwards(ConstIntBound(0b11), -1)
    assert check_knownbits_string(r, "??11")
    x = knownbits( 0b10000,     # ?...?10???
                  ~0b11000)
    r = x.int_and_backwards(ConstIntBound(0b11), 0)
    assert check_knownbits_string(r, "??10?00")
    x = knownbits( 0b1010,      # ?...?1010
                  ~0b1111)
    r = x.int_and_backwards(ConstIntBound(0b11), 0)
    assert check_knownbits_string(r, "??1000") # inconsistent: result wins
    x = IntUnbounded()
    r = x.int_and_backwards(ConstIntBound(0b11), 0b10)
    assert check_knownbits_string(r, "??10")

def test_knownbits_int_and_backward_example():
    x = IntUnbounded()
    o = knownbits(0b101010,
                  0b010100) # 1?1?10
    r = x.int_and_backwards(o, 0b111)
    assert check_knownbits_string(r, "??0?0?1?")

@given(constant, constant)
def test_const_stays_const_or(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    r = b1.or_bound(b2)
    assert r.is_constant()
    assert r.equals(n1 | n2)
    assert r.get_constant_int() == n1 | n2

@given(constant, constant)
def test_const_stays_const_and(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    r = b1.and_bound(b2)
    assert r.is_constant()
    assert r.equals(n1 & n2)
    assert r.get_constant_int() == n1 & n2

@given(constant, constant)
def test_const_stays_const_xor(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    r = b1.xor_bound(b2)
    assert r.is_constant()
    assert r.equals(n1 ^ n2)
    assert r.get_constant_int() == n1 ^ n2

@given(constant)
def test_const_stays_const_invert(t1):
    b1, n1 = t1
    r = b1.invert_bound()
    assert r.is_constant()
    assert r.equals(~n1)
    assert r.get_constant_int() == ~n1

@given(constant, constant)
def test_const_stays_const_lshift(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    r = b1.lshift_bound(b2)
    if n2 >= LONG_BIT:
        assert r.is_constant()
        assert r.equals(0)
    elif n2 >= 0:
        assert r.is_constant()
        assert r.equals(intmask(n1 << n2))

@given(constant, constant)
def test_const_stays_const_urshift(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    r = b1.urshift_bound(b2)
    if n2 >= LONG_BIT:
        assert r.is_constant()
        assert r.equals(0)
    elif n2 >= 0:
        assert r.is_constant()
        assert r.equals(intmask(r_uint(n1) >> r_uint(n2)))

@given(constant, constant)
def test_const_stays_const_rshift(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    r = b1.rshift_bound(b2)
    if n2 >= LONG_BIT:
        assert r.is_constant()
        if n1 < 0:
            assert r.equals(-1)
        else:
            assert r.equals(0)
    elif n2 >= 0:
        assert r.is_constant()
        assert r.equals(intmask(n1) >> intmask(n2))


@given(maybe_valid_value_mask_pair)
def test_validtnum_assertion_random(t1):
    # this one does both positive and negative examples
    val, msk = t1
    is_valid = (0 == val & msk)
    if is_valid:
        b = knownbits(val, msk)
    else:
        with pytest.raises(Exception):
            b = knownbits(val, msk)

@given(knownbits_with_contained_number, knownbits_with_contained_number)
def test_knownbits_or_random(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    b3 = b1.or_bound(b2)
    r = n1 | n2
    assert b3.contains(r)

@given(knownbits_with_contained_number, knownbits_with_contained_number)
def test_knownbits_and_random(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    b3 = b1.and_bound(b2)
    r = n1 & n2
    assert b3.contains(r)

@given(knownbits_with_contained_number, knownbits_with_contained_number)
def test_knownbits_xor_random(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    b3 = b1.xor_bound(b2)
    r = n1 ^ n2
    assert b3.contains(r)

@given(knownbits_with_contained_number)
def test_knownbits_invert_random(t1):
    b1, n1 = t1
    b2 = b1.invert_bound()
    r = ~n1
    assert b2.contains(r)

@given(knownbits_with_contained_number, pos_relatively_small_values)
def test_knownbits_lshift_random(t1, t2):
    b1, n1 = t1
    b2 = ConstIntBound(t2)
    print b1, " << ", t2
    r = b1.lshift_bound(b2)
    # this works for left-shift, not for right-shift!
    assert r.contains(intmask(u(n1) << u(t2)))

@given(knownbits_with_contained_number, pos_relatively_small_values)
def test_knownbits_rshift_signed_random(t1, t2):
    b1, n1 = t1
    b2 = ConstIntBound(t2)
    print b1, " >> ", t2
    r = b1.rshift_bound(b2)
    assert r.contains(n1 >> t2)

@given(knownbits_with_contained_number, pos_relatively_small_values)
def test_knownbits_rshift_unsigned_random(t1, t2):
    b1, n1 = t1
    b2 = ConstIntBound(t2)
    print b1, " >> ", t2
    r = b1.urshift_bound(b2)
    assert r.contains(intmask(u(n1) >> u(t2)))
    if n1 < 0 and t2 > 0 and r.is_constant():
        assert r.get_constant_int() >= 0

@given(knownbits_with_contained_number, knownbits_with_contained_number)
def test_knownbits_add_random(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    print t1, " + ", t2
    r = b1.add_bound(b2)
    assert r.contains(intmask(n1 + n2))

@given(knownbits_with_contained_number, knownbits_with_contained_number)
def test_knownbits_sub_random(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    print t1, " - ", t2
    r = b1.sub_bound(b2)
    assert r.contains(intmask(n1 - n2))

@given(knownbits_with_contained_number, ints)
def test_knownbits_add_concrete_random(t1, t2):
    b1, n1 = t1
    print t1, " + ", t2
    r = b1.add(t2)
    assert r.contains(intmask(n1 + t2))

@given(knownbits_with_contained_number)
def test_knownbits_neg_random(t1):
    b1, n1 = t1
    print "neg(", t1, ")"
    r = b1.neg_bound()
    if n1 != -sys.maxint-1:
        assert r.contains(-n1)

@given(ints)
def test_knownbits_neg_const(t1):
    b1 = ConstIntBound(t1)
    r = b1.neg_bound()
    if t1 != -sys.maxint-1:
        assert r.is_constant()
        assert r.equals(-t1)


def knownbits(tvalue, tmask=0, do_unmask=False):
    if not isinstance(tvalue, r_uint):
        tvalue = u(tvalue)
    if not isinstance(tmask, r_uint):
        tmask = u(tmask)
    return IntBoundKnownbits(tvalue, tmask, do_unmask)

def u(signed_int):
    return r_uint(signed_int)

def check_knownbits_string(r, lower_bits, upper_fill='?'):
    return r.knownbits_string() == upper_fill*(LONG_BIT-len(lower_bits)) + lower_bits

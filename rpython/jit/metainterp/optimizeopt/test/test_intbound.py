import pytest
from rpython.jit.metainterp.optimizeopt.intutils import IntBound, IntUpperBound, \
     IntLowerBound, IntUnbounded, ConstIntBound, next_pow2_m1, MININT, MAXINT

from copy import copy
import sys
from rpython.rlib.rarithmetic import LONG_BIT, ovfcheck, intmask, r_uint

from hypothesis import given, strategies, example

special_values = (
    range(-100, 100) +
    [2 ** i for i in range(1, LONG_BIT)] +
    [-2 ** i for i in range(1, LONG_BIT)] +
    [2 ** i - 1 for i in range(1, LONG_BIT)] +
    [-2 ** i - 1 for i in range(1, LONG_BIT)] +
    [2 ** i + 1 for i in range(1, LONG_BIT)] +
    [-2 ** i + 1 for i in range(1, LONG_BIT)] +
    [sys.maxint, -sys.maxint-1])

special_values = strategies.sampled_from(
    [int(v) for v in special_values if type(int(v)) is int])

ints = strategies.builds(
    int, # strategies.integers sometimes returns a long?
    special_values | strategies.integers(
    min_value=int(-sys.maxint-1), max_value=sys.maxint))

ints_or_none = strategies.none() | ints

def bound_eq(a, b):
    return a.contains_bound(b) and b.contains_bound(a)

def bound(a, b):
    if a is None and b is None:
        return IntUnbounded()
    elif a is None:
        return IntUpperBound(b)
    elif b is None:
        return IntLowerBound(a)
    else:
        return IntBound(a, b)

def const(a):
    return bound(a,a)


def build_bound_with_contained_number(a, b, c):
    a, b, c = sorted([a, b, c])
    r = bound(a, c)
    assert r.contains(b)
    return r, b

unbounded = strategies.builds(
    lambda x: (bound(None, None), int(x)),
    ints
)

lower_bounded = strategies.builds(
    lambda x, y: (bound(min(x, y), None), max(x, y)),
    ints,
    ints
)

upper_bounded = strategies.builds(
    lambda x, y: (bound(None, max(x, y)), min(x, y)),
    ints,
    ints
)

bounded = strategies.builds(
    build_bound_with_contained_number,
    ints, ints, ints
)

constant = strategies.builds(
    lambda x: (const(x), x),
    ints
)

bound_with_contained_number = strategies.one_of(
    unbounded, lower_bounded, upper_bounded, constant, bounded)

def some_bounds():
    brd = [None] + range(-2, 3)
    for lower in brd:
        for upper in brd:
            if lower is not None and upper is not None and lower > upper:
                continue
            yield (lower, upper, bound(lower, upper))

nbr = range(-5, 6)

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

def test_make_ne():
    ge = IntUnbounded()
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
    from rpython.jit.metainterp.optimize import InvalidLoop
    b1 = bound(17, 17)
    b2 = bound(1, 1)
    with pytest.raises(InvalidLoop):
        b1.intersect(b2)

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
    r = b.add_bound(ConstIntBound(1))
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

    for b in (b10, b100, bmax, IntBound(0, 0)):
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

    a = bound(0, 0).sub_bound(bound(0, None))
    assert a.lower == -MAXINT
    assert a.upper == 0

    a = bound(0, 0).sub_bound(bound(None, 0))
    assert a.lower == MININT
    assert a.upper == MAXINT


def test_sub_bound_bug():
    b = bound(MININT, MAXINT)
    bval = MININT
    assert b.contains(bval)
    r = b.sub_bound(ConstIntBound(1))
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

def test_or_bound():
    for _, _, b1 in some_bounds():
        for _, _, b2 in some_bounds():
            b3 = b1.or_bound(b2)
            for n1 in nbr:
                for n2 in nbr:
                    if b1.contains(n1) and b2.contains(n2):
                        assert b3.contains(n1 | n2)
                        assert b3.contains(n1 ^ n2) # we use it for xor too


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

def test_widen():
    for _, _, b1 in some_bounds():
        b2 = b1.widen()
        assert b2.contains_bound(b1)
    b = bound(MININT + 1, MAXINT).widen()
    assert b.contains_bound(bound(None, None))
    b = bound(MININT, MAXINT - 1).widen()
    assert b.contains_bound(bound(None, None))
    b = bound(-10, 10)
    b1 = b.widen()
    assert bound_eq(b, b1)


@given(bound_with_contained_number, bound_with_contained_number)
def test_make_random(t1, t2):
    def d(b):
        return b.lower, b.upper
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
    # first check that 0 + b1 is b1
    b1viaadd0 = b1.add_bound(bound(0, 0))
    assert bound_eq(b1, b1viaadd0)

    b2, n2 = t2
    print b1, n1
    print b2, n2
    b3 = b1.add_bound(b2)
    b3noovf = b1.add_bound_no_overflow(b2)
    try:
        r = ovfcheck(n1 + n2)
    except OverflowError:
        assert not b1.add_bound_cannot_overflow(b2)
    else:
        assert b3.contains(r)
        assert b3noovf.contains(r)
    # the result bound also works for unsigned addition, regardless of overflow
    assert b3.contains(intmask(r_uint(n1) + r_uint(n2)))
    assert b3.contains_bound(b3noovf) # b3noovf must always be smaller than b3

    # check consistency with int_sub
    b3viasub = b1.sub_bound(b2.neg_bound())
    # b3viasub is sometimes less precise than than b3, because b2.neg_bound()
    # has an extra overflow possibility if it contains MININT. Therefore we
    # can't check equality, only containment:
    assert b3viasub.contains_bound(b3)
    if not b2.contains(MININT):
        assert b3.contains_bound(b3viasub)

@example((bound(-100, None), -99), (bound(None, -100), -100))
@given(bound_with_contained_number, bound_with_contained_number)
def test_sub_bound_random(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    print b1, n1
    print b2, n2
    b3 = b1.sub_bound(b2)
    b3noovf = b1.sub_bound_no_overflow(b2)
    try:
        r = ovfcheck(n1 - n2)
    except OverflowError:
        assert not b1.sub_bound_cannot_overflow(b2)
    else:
        assert b3.contains(r)
        assert b3noovf.contains(r)
    # the result bound also works for unsigned subtraction, regardless of overflow
    assert b3.contains(intmask(r_uint(n1) - r_uint(n2)))
    assert b3.contains_bound(b3noovf) # b3noovf must always be smaller than b3

    # check consistency with int_add
    b3viaadd = b1.add_bound(b2.neg_bound())
    assert b3viaadd.contains_bound(b3)
    if not b2.contains(MININT):
        assert b3.contains_bound(b3viaadd)


@given(bound_with_contained_number, bound_with_contained_number)
def test_mul_bound_random(t1, t2):
    b1, n1 = t1
    b2, n2 = t2
    b3 = b1.mul_bound(b2)
    try:
        r = ovfcheck(n1 * n2)
    except OverflowError:
        assert not b1.mul_bound_cannot_overflow(b2)
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


shift_amount = strategies.builds(
    build_bound_with_contained_number,
    *(strategies.integers(min_value=0, max_value=LONG_BIT), ) * 3
)


@given(bound_with_contained_number, shift_amount)
def test_lshift_bound_random(t1, t2):
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
@example((IntBound(-sys.maxint - 1, -sys.maxint+10), -sys.maxint-1))
def test_neg_bound_random(t1):
    b1, n1 = t1
    b2 = b1.neg_bound()
    if n1 != -sys.maxint - 1:
        assert b2.contains(-n1)
    else:
        assert b2.upper == MAXINT

    # check that it's always correct for unsigned negation
    b2.contains(intmask(-r_uint(n1)))

    # always check MININT
    if b1.contains(MININT):
        assert b2.contains(MININT)

    # check consistency with sub_bound
    b2viasub = ConstIntBound(0).sub_bound(b1)
    assert b2viasub.contains_bound(b2)
    #assert b2.contains_bound(b2viasub)

@given(bound_with_contained_number)
def test_widen_random(t):
    b, n = t
    b1 = b.widen()
    assert b1.contains_bound(b)

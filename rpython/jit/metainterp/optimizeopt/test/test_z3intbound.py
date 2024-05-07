""" The purpose of this test file is to do bounded model checking of the
IntBound methods with Z3.

The approach is to generate random bounds, then perform operations on them, and
ask Z3 whether the resulting bound is a sound approximation of the result.
"""

import pytest
import sys

from rpython.rlib.rarithmetic import LONG_BIT, r_uint, intmask
from rpython.jit.metainterp.optimizeopt.intutils import IntBound

try:
    import z3
    from hypothesis import given, strategies, assume
except ImportError:
    pytest.skip("please install z3 (z3-solver on pypi) and hypothesis")

def BitVecVal(value):
    return z3.BitVecVal(value, LONG_BIT)

def BitVec(name):
    return z3.BitVec(name, LONG_BIT)

MAXINT = sys.maxint
MININT = -sys.maxint - 1

uints = strategies.builds(
    r_uint,
    strategies.integers(min_value=0, max_value=2**LONG_BIT - 1)
)

ints = strategies.builds(
    lambda x: intmask(r_uint(x)),
    strategies.integers(min_value=0, max_value=2**LONG_BIT - 1)
)

def build_some_bits_known(a, b):
    return IntBound(tvalue=a & ~b, tmask=b)

some_bits_known = strategies.builds(
    build_some_bits_known,
    uints, uints
)

bounds = some_bits_known

varname_counter = 0

def to_z3(bound, variable=None):
    global varname_counter
    if variable is None:
        variable = z3.BitVec("bv%s" % (varname_counter, ), LONG_BIT)
        varname_counter += 1
    components = []
    if bound.upper < MAXINT:
        components.append(variable <= z3.BitVecVal(bound.upper, LONG_BIT))
    if bound.lower > MININT:
        components.append(variable >= z3.BitVecVal(bound.lower, LONG_BIT))
    if bound.tmask != r_uint(-1): # all unknown:
        components.append(variable & z3.BitVecVal(~bound.tmask, LONG_BIT) == z3.BitVecVal(bound.tvalue, LONG_BIT))
    if len(components) == 1:
        return variable, components[0]
    if len(components) == 0:
        return variable, z3.BoolVal(True)
    return variable, z3.And(*components)

class CheckError(Exception):
    pass


def prove_implies(*args):
    last = args[-1]
    prev = args[:-1]
    return prove(z3.Implies(z3.And(*prev), last))

def prove(cond):
    solver = z3.Solver()
    if pytest.config.option.z3timeout:
        solver.set("timeout", pytest.config.option.z3timeout)
    z3res = solver.check(z3.Not(cond))
    if z3res == z3.unsat:
        pass
    elif z3res == z3.unknown:
        print "timeout", cond
    elif z3res == z3.sat:
        # not possible to prove!
        # print some nice stuff
        model = solver.model()
        raise CheckError("%s\n%s" % (cond, model))

@given(bounds, bounds)
def test_add(b1, b2):
    b3 = b1.add_bound(b2)
    var1, formula1 = to_z3(b1)
    var2, formula2 = to_z3(b2)
    var3, formula3 = to_z3(b3, var1 + var2)
    prove_implies(formula1, formula2, formula3)

@given(bounds, bounds)
def test_add_bound_cannot_overflow(b1, b2):
    bound = b1.add_bound_cannot_overflow(b2)
    assume(bound)
    var1, formula1 = to_z3(b1)
    var2, formula2 = to_z3(b2)
    m = z3.SignExt(LONG_BIT, var1) + z3.SignExt(LONG_BIT, var2)
    no_ovf = m == z3.SignExt(LONG_BIT, var1 + var2)
    prove_implies(formula1, formula2, no_ovf)

@given(bounds, bounds)
def test_add_bound_no_overflow(b1, b2):
    b3 = b1.add_bound_no_overflow(b2)
    var1, formula1 = to_z3(b1)
    var2, formula2 = to_z3(b2)
    var3, formula3 = to_z3(b3, var1 + var2)
    m = z3.SignExt(LONG_BIT, var1) + z3.SignExt(LONG_BIT, var2)
    no_ovf = m == z3.SignExt(LONG_BIT, var1 + var2)
    prove_implies(formula1, formula2, no_ovf, formula3)

@given(bounds, bounds)
def test_sub(b1, b2):
    b3 = b1.sub_bound(b2)
    var1, formula1 = to_z3(b1)
    var2, formula2 = to_z3(b2)
    var3, formula3 = to_z3(b3, var1 - var2)
    prove_implies(formula1, formula2, formula3)

@given(bounds, bounds)
def test_sub_bound_cannot_overflow(b1, b2):
    bound = b1.sub_bound_cannot_overflow(b2)
    assume(bound)
    var1, formula1 = to_z3(b1)
    var2, formula2 = to_z3(b2)
    m = z3.SignExt(LONG_BIT, var1) - z3.SignExt(LONG_BIT, var2)
    no_ovf = m == z3.SignExt(LONG_BIT, var1 - var2)
    prove_implies(formula1, formula2, no_ovf)

@given(bounds, bounds)
def test_sub_bound_no_overflow(b1, b2):
    b3 = b1.sub_bound_no_overflow(b2)
    var1, formula1 = to_z3(b1)
    var2, formula2 = to_z3(b2)
    var3, formula3 = to_z3(b3, var1 - var2)
    m = z3.SignExt(LONG_BIT, var1) - z3.SignExt(LONG_BIT, var2)
    no_ovf = m == z3.SignExt(LONG_BIT, var1 - var2)
    prove_implies(formula1, formula2, no_ovf, formula3)

@given(bounds, bounds)
def test_mul(b1, b2):
    b3 = b1.mul_bound(b2)
    var1, formula1 = to_z3(b1)
    var2, formula2 = to_z3(b2)
    var3, formula3 = to_z3(b3, var1 * var2)
    prove_implies(formula1, formula2, formula3)

@given(bounds, bounds)
def test_mul_bound_cannot_overflow(b1, b2):
    bound = b1.mul_bound_cannot_overflow(b2)
    assume(bound)
    var1, formula1 = to_z3(b1)
    var2, formula2 = to_z3(b2)
    m = z3.SignExt(LONG_BIT, var1) * z3.SignExt(LONG_BIT, var2)
    no_ovf = m == z3.SignExt(LONG_BIT, var1 * var2)
    prove_implies(formula1, formula2, no_ovf)

@given(bounds, bounds)
def test_mul_bound_no_overflow(b1, b2):
    b3 = b1.mul_bound_no_overflow(b2)
    var1, formula1 = to_z3(b1)
    var2, formula2 = to_z3(b2)
    var3, formula3 = to_z3(b3, var1 * var2)
    m = z3.SignExt(LONG_BIT, var1) * z3.SignExt(LONG_BIT, var2)
    no_ovf = m == z3.SignExt(LONG_BIT, var1 * var2)
    prove_implies(formula1, formula2, no_ovf, formula3)

@given(bounds)
def test_neg(b1):
    b2 = b1.neg_bound()
    var1, formula1 = to_z3(b1)
    var2, formula2 = to_z3(b2, -var1)
    prove_implies(formula1, formula2)

# ____________________________________________________________
# boolean operations

@given(bounds, bounds)
def test_and(b1, b2):
    b3 = b1.and_bound(b2)
    var1, formula1 = to_z3(b1)
    var2, formula2 = to_z3(b2)
    var3, formula3 = to_z3(b3, var1 & var2)
    prove_implies(formula1, formula2, formula3)

@given(bounds, bounds)
def test_or(b1, b2):
    b3 = b1.or_bound(b2)
    var1, formula1 = to_z3(b1)
    var2, formula2 = to_z3(b2)
    var3, formula3 = to_z3(b3, var1 | var2)
    prove_implies(formula1, formula2, formula3)

@given(bounds, bounds)
def test_xor(b1, b2):
    b3 = b1.xor_bound(b2)
    var1, formula1 = to_z3(b1)
    var2, formula2 = to_z3(b2)
    var3, formula3 = to_z3(b3, var1 ^ var2)
    prove_implies(formula1, formula2, formula3)

@given(bounds)
def test_invert(b1):
    b2 = b1.invert_bound()
    var1, formula1 = to_z3(b1)
    var2, formula2 = to_z3(b2, ~var1)
    prove_implies(formula1, formula2)


# ____________________________________________________________
# shrinking

@given(ints, ints)
def test_shrink_bounds_to_knownbits(x, y):
    x, y = min(x, y), max(x, y)
    b = IntBound(x, y, do_shrinking=False)
    var1, formula1 = to_z3(b)
    b.shrink()
    var1, formula2 = to_z3(b, var1)
    prove_implies(formula1, formula2)


@given(uints, uints)
def test_shrink_knownbits_to_bounds(x, y):
    b = IntBound(tvalue=x & ~y, tmask=y, do_shrinking=False)
    var1, formula1 = to_z3(b)
    b.shrink()
    var1, formula2 = to_z3(b, var1)
    prove_implies(formula1, formula2)


# ____________________________________________________________
# backwards tests

@given(uints, uints, ints, strategies.data())
def test_and_backwards(x, tmask, other_const, data):
    tvalue = x & ~tmask
    b = IntBound(tvalue=x & ~tmask, tmask=tmask)
    x = intmask(x)
    assert b.contains(x)
    space_at_bottom = x - b.lower
    shrink_by = data.draw(strategies.integers(0, space_at_bottom - 1))
    b.make_ge_const(b.lower + shrink_by)
    assert b.contains(x)
    space_at_top = b.upper - x
    if space_at_top:
        shrink_by = data.draw(strategies.integers(0, space_at_top - 1))
        b.make_le_const(b.upper - shrink_by)
        assert b.contains(x)
    # now we have a bound b, and a value x in that bound
    # we now model this situation:
    # i1 = int_and(i0, <other_const>)
    # guard_value(i1, <res>)
    # with that info we can improve the bound of i0
    res = x & other_const
    other_bound = IntBound(other_const, other_const)
    better_b_bound = b.and_bound_backwards(other_bound, res)

    var1, formula1 = to_z3(b)
    var2, formula2 = to_z3(better_b_bound, var1)
    prove_implies(formula1, BitVecVal(res) == BitVecVal(other_const) & var1, formula2)
    b.intersect(better_b_bound)

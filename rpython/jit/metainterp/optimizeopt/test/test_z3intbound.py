""" The purpose of this test file is to do bounded model checking of the
IntBound methods with Z3.

The approach is to generate random bounds, then perform operations on them, and
ask Z3 whether the resulting bound is a sound approximation of the result.
"""

import pytest
import sys
import gc

from rpython.rlib.rarithmetic import LONG_BIT, r_uint, intmask
from rpython.jit.metainterp.optimizeopt.intutils import (
    IntBound,
    _tnum_add,
    _tnum_and,
    _tnum_and_backwards,
    unmask_one,
    unmask_zero,
    _tnum_improve_knownbits_by_bounds_helper,
)
from rpython.jit.metainterp.optimize import InvalidLoop

from rpython.jit.metainterp.optimizeopt.test.test_intbound import knownbits_and_bound_with_contained_number

try:
    import z3
    from hypothesis import given, strategies, assume, example
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

bounds = strategies.builds(
    lambda tup: tup[0],
    knownbits_and_bound_with_contained_number
)

varname_counter = 0

def z3_tnum_condition(variable, tvalue, tmask):
    if isinstance(tvalue, r_uint):
        tvalue = BitVecVal(tvalue)
    if isinstance(tmask, r_uint):
        tmask = BitVecVal(tmask)
    return variable & ~tmask == tvalue

def z3_tvalue_tmask_are_valid(tvalue, tmask):
    return tvalue & ~tmask == tvalue

def to_z3(bound, variable=None):
    global varname_counter
    if variable is None:
        variable = BitVec("bv%s" % (varname_counter, ))
        varname_counter += 1
    components = []
    if bound.upper < MAXINT:
        components.append(variable <= BitVecVal(bound.upper))
    if bound.lower > MININT:
        components.append(variable >= BitVecVal(bound.lower))
    if bound.tmask != r_uint(-1): # all unknown:
        components.append(z3_tnum_condition(variable, bound.tvalue, bound.tmask))
    if len(components) == 1:
        return variable, components[0]
    if len(components) == 0:
        return variable, z3.BoolVal(True)
    return variable, z3.And(*components)

class CheckError(Exception):
    pass


def prove_implies(*args, **kwargs):
    last = args[-1]
    prev = args[:-1]
    return prove(z3.Implies(z3.And(*prev), last), **kwargs)

def teardown_function(function):
    # z3 doesn't add enough memory pressure, just collect after every function
    # to counteract
    gc.collect()

def prove(cond, use_timeout=True):
    solver = z3.Solver()
    if use_timeout and pytest.config.option.z3timeout:
        solver.set("timeout", pytest.config.option.z3timeout)
    z3res = solver.check(z3.Not(cond))
    if z3res == z3.unsat:
        pass
    elif z3res == z3.unknown:
        print "timeout", cond
        assert use_timeout
    elif z3res == z3.sat:
        # not possible to prove!
        model = solver.model()
        raise CheckError(cond, model)

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
    if bound:
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

@given(bounds, bounds)
def test_known(b1, b2):
    var1, formula1 = to_z3(b1)
    var2, formula2 = to_z3(b2)
    if b1.known_lt(b2):
        prove_implies(formula1, formula2, var1 < var2)
    if b1.known_gt(b2):
        prove_implies(formula1, formula2, var1 > var2)
    if b1.known_le(b2):
        prove_implies(formula1, formula2, var1 <= var2)
    if b1.known_ge(b2):
        prove_implies(formula1, formula2, var1 >= var2)
    if b1.known_ne(b2):
        prove_implies(formula1, formula2, var1 != var2)

@given(bounds, bounds)
def test_known_unsigned(b1, b2):
    var1, formula1 = to_z3(b1)
    var2, formula2 = to_z3(b2)
    if b1.known_unsigned_lt(b2):
        prove_implies(formula1, formula2, z3.ULT(var1, var2))
    if b1.known_unsigned_gt(b2):
        prove_implies(formula1, formula2, z3.UGT(var1, var2))
    if b1.known_unsigned_le(b2):
        prove_implies(formula1, formula2, z3.ULE(var1, var2))
    if b1.known_unsigned_ge(b2):
        prove_implies(formula1, formula2, z3.UGE(var1, var2))


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

@example(b1=IntBound.from_constant(-100), b2=IntBound.from_constant(-100))
@given(bounds, bounds)
def test_intersect(b1, b2):
    var1, formula1 = to_z3(b1)
    _, formula2 = to_z3(b2, var1)
    both_conditions = z3.And(formula1, formula2)
    solver = z3.Solver()
    intersection_nonempty = solver.check(both_conditions) == z3.sat
    try:
        b1.intersect(b2)
    except InvalidLoop:
        assert intersection_nonempty == False
    else:
        _, formula3 = to_z3(b1, var1)
        prove_implies(both_conditions, formula3)
        assert intersection_nonempty

# ____________________________________________________________
# shrinking

@given(ints, ints)
def test_shrink_bounds_to_knownbits(x, y):
    x, y = sorted([x, y])
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

@given(ints, ints, uints, uints)
def test_shrink_mixed(x, y, value, tmask):
    x, y = sorted([x, y])
    b = IntBound(x, y, value & ~tmask, tmask, do_shrinking=False)
    var1, formula1 = to_z3(b)
    # check that b contains values before we shrink
    solver = z3.Solver()
    assume(solver.check(formula1) == z3.sat)
    b.shrink()
    var1, formula2 = to_z3(b, var1)
    prove_implies(formula1, formula2)

# ____________________________________________________________
# backwards tests

@given(uints, uints, ints, strategies.data())
def test_and_backwards(x, tmask, other_const, data):
    tvalue = x & ~tmask
    b = IntBound(tvalue=tvalue, tmask=tmask)
    x = intmask(x)
    assert b.contains(x)
    space_at_bottom = x - b.lower
    if space_at_bottom:
        shrink_by = data.draw(strategies.integers(0, space_at_bottom - 1))
        b.make_ge_const(int(b.lower + shrink_by))
        assert b.contains(x)
    space_at_top = b.upper - x
    if space_at_top:
        shrink_by = data.draw(strategies.integers(0, space_at_top - 1))
        b.make_le_const(int(b.upper - shrink_by))
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


# ____________________________________________________________
# explicit proofs

def make_z3_tnum(name):
    """ make a z3 knownbits number. returns a tuple of:
    - variable, corresponding to the concrete value
    - tvalue and tmask, corresponding to the abstract value
    - formula, which is the precondition that tvalue and tmask are well-formed,
      and that they are a valid abstraction of the concrete value
    """
    variable = BitVec(name)
    tvalue = BitVec(name + "_tvalue")
    tmask = BitVec(name + "_tmask")
    formula = z3.And(
        # is the tnum well-formed? ie are the unknown bits in tvalue set to 0?
        tvalue & ~tmask == tvalue,
        # does variable fulfill the conditions imposed by tvalue and tmask?
        z3_tnum_condition(variable, tvalue, tmask)
    )
    return variable, tvalue, tmask, formula

def make_z3_bound_and_tnum(name):
    """ same as make_z3_tnum, but also give the abstract number a bound. the
    return values are:
    - variable, corresponding to the concrete value
    - lower, a variable corresponding to the lower bound
    - upper, a variable corresponding to the upper bound
    - tvalue and tmask, corresponding to the abstract value
    - formula, which is the precondition that tvalue and tmask are well-formed,
      that lower <= upper, and that the four variables are a valid abstraction
      of the concrete value
    """
    variable = BitVec(name)
    tvalue = BitVec(name + "_tvalue")
    tmask = BitVec(name + "_tmask")
    upper = BitVec(name + "_upper")
    lower = BitVec(name + "_lower")
    formula = z3.And(
        z3_tnum_condition(variable, tvalue, tmask),
        lower <= variable,
        variable <= upper
    )
    return variable, lower, upper, tvalue, tmask, formula

def model_to_intbound_instance(model, tvalue, tmask, lower=None, upper=None):
    """ A helper function that can be used to turn a Z3 counterexample into an
    IntBound instance to understand it better. """
    assert (upper is None) == (lower is None)
    v = r_uint(model.evaluate(tvalue).as_long())
    m = r_uint(model.evaluate(tmask).as_long())
    if upper is lower is None:
        return IntBound.from_knownbits(v, m)
    l = model.evaluate(lower).as_signed_long()
    u = model.evaluate(upper).as_signed_long()
    return IntBound(l, u, v, m)

def test_prove_and():
    self_variable, self_tvalue, self_tmask, self_formula = make_z3_tnum('self')
    other_variable, other_tvalue, other_tmask, other_formula = make_z3_tnum('other')
    result = BitVec('result')
    res_tvalue, res_tmask = _tnum_and(self_tvalue, self_tmask, other_tvalue, other_tmask)
    prove_implies(
        self_formula,
        other_formula,
        result == self_variable & other_variable,
        z3_tnum_condition(result, res_tvalue, res_tmask),
    )

def test_prove_and_bounds_logic():
    self_variable = BitVec('self')
    other_variable = BitVec('other')
    result = BitVec('result')
    prove_implies(
        result == self_variable & other_variable,
        self_variable >= 0,
        result >= 0,
        use_timeout=False
    )
    prove_implies(
        result == self_variable & other_variable,
        other_variable >= 0,
        result >= 0,
        use_timeout=False
    )
    prove_implies(
        result == self_variable & other_variable,
        self_variable >= 0,
        result <= self_variable,
        use_timeout=False
    )
    prove_implies(
        result == self_variable & other_variable,
        other_variable >= 0,
        result <= other_variable,
        use_timeout=False
    )

def test_prove_and_backwards():
    self_variable, self_tvalue, self_tmask, self_formula = make_z3_tnum('self')
    other_variable, other_tvalue, other_tmask, other_formula = make_z3_tnum('other')
    res = self_variable & other_variable
    better_tvalue, better_tmask = _tnum_and_backwards(self_tvalue, self_tmask, other_tvalue, other_tmask, res)
    prove_implies(
        self_formula,
        other_formula,
        self_variable & other_variable == res,
        z3_tnum_condition(self_variable, better_tvalue, better_tmask),
        use_timeout=False
    )

def test_prove_add():
    self_variable, self_tvalue, self_tmask, self_formula = make_z3_tnum('self')
    other_variable, other_tvalue, other_tmask, other_formula = make_z3_tnum('other')
    result = BitVec('result')
    res_tvalue, res_tmask = _tnum_add(self_tvalue, self_tmask, other_tvalue, other_tmask)
    prove_implies(
        self_formula,
        other_formula,
        result == self_variable + other_variable,
        z3_tnum_condition(result, res_tvalue, res_tmask),
        use_timeout=False
    )

def test_prove_unmask_one_gives_unsigned_max():
    self_variable, self_tvalue, self_tmask, self_formula = make_z3_tnum('self')
    max_self = unmask_one(self_tvalue, self_tmask)
    prove_implies(
        self_formula,
        z3.ULE(self_variable, max_self),
        use_timeout=False
    )

def test_prove_unmask_zero_gives_unsigned_min():
    self_variable, self_tvalue, self_tmask, self_formula = make_z3_tnum('self')
    min_self = unmask_zero(self_tvalue, self_tmask)
    prove_implies(
        self_formula,
        z3.ULE(min_self, self_variable),
        use_timeout=False
    )

def test_prove_known_unsigned_lt():
    self_variable, self_tvalue, self_tmask, self_formula = make_z3_tnum('self')
    other_variable, other_tvalue, other_tmask, other_formula = make_z3_tnum('other')
    max_self = unmask_one(self_tvalue, self_tmask)
    min_other = unmask_zero(other_tvalue, other_tmask)
    prove_implies(
        self_formula,
        other_formula,
        z3.ULT(max_self, min_other),
        z3.ULT(self_variable, other_variable),
        use_timeout=False
    )

def test_prove_known_unsigned_lt_from_signed_lt():
    self_variable, self_lower, self_upper, self_tvalue, self_tmask, self_formula = make_z3_bound_and_tnum('self')
    other_variable, other_lower, other_upper, other_tvalue, other_tmask, other_formula = make_z3_bound_and_tnum('other')
    max_self = unmask_one(self_tvalue, self_tmask)
    min_other = unmask_zero(other_tvalue, other_tmask)
    prove_implies(
        self_formula,
        other_formula,
        self_lower >= 0,
        self_upper < other_lower,
        z3.ULT(self_variable, other_variable),
        use_timeout=False
    )

def popcount64(w):
    w -= (w >> 1) & 0x5555555555555555
    w = (w & 0x3333333333333333) + ((w >> 2) & 0x3333333333333333)
    w = (w + (w >> 4)) & 0x0f0f0f0f0f0f0f0f
    return ((w * 0x0101010101010101) >> 56) & 0xff

def test_popcount64():
    assert popcount64(1 << 60) == 1
    assert popcount64((1 << 60) + 5) == 3
    assert popcount64((1 << 63) + 0b11010110111) == 9

def test_prove_shrink_knownbits_by_bounds():
    self_variable, self_lower, self_upper, self_tvalue, self_tmask, self_formula = make_z3_bound_and_tnum('self')
    new_tvalue, new_tmask, bounds_common, hbm_bounds = _tnum_improve_knownbits_by_bounds_helper(self_tvalue, self_tmask, self_lower, self_upper)
    prove_implies(
        # if tvalue and tmask are a valid encoding
        self_tvalue & ~self_tmask == self_tvalue,
        # and the ranges hold
        self_variable <= self_upper,
        self_lower <= self_variable,
        # then the two sets defined by old and new knownbits are equivalent
        z3_tnum_condition(self_variable, self_tvalue, self_tmask) ==
            z3_tnum_condition(self_variable, new_tvalue, new_tmask),
        use_timeout=False
    )
    prove_implies(
        # if tvalue and tmask are a valid encoding
        self_tvalue & ~self_tmask == self_tvalue,
        # and the ranges hold
        self_variable <= self_upper,
        self_lower <= self_variable,
        # then we cannot have *fewer* known bits afterwards,
        popcount64(~new_tmask) >= popcount64(~self_tmask),
        use_timeout=False,
    )
    prove_implies(
        self_formula,
        # this used to be an assert in the code. now we prove it (and remove it
        # from the code). the assert checks agreement between bounds and
        # knownbits
        unmask_zero(bounds_common, self_tmask) == self_tvalue & hbm_bounds
    )

class Z3IntBound(IntBound):
    def __init__(self, lower, upper, tvalue, tmask, concrete_variable=None):
        self.lower = lower
        self.upper = upper
        self.tvalue = tvalue
        self.tmask = tmask

        self.concrete_variable = concrete_variable

    @staticmethod
    def new(lower, upper, tvalue, tmask):
        return Z3IntBound(lower, upper, tvalue, tmask)

    def __repr__(self):
        more = ''
        if self.concrete_variable is not None:
            more = ', concrete_variable=%s' % (self.concrete_variable, )
        return "<Z3IntBound lower=%s, upper=%s, tvalue=%s, tmask=%s%s>" % (
            self.lower, self.upper, self.tvalue, self.tmask, more)

    def z3_formula(self, variable=None):
        """ return the Z3 condition that:
        - self is well-formed
        - variable (or self.concrete_variable) is an element of the set
          described by self
        """
        if variable is None:
            variable = self.concrete_variable
            assert variable is not None
        return z3.And(
            # is the tnum well-formed? ie are the unknown bits in tvalue set to 0?
            self.tvalue & ~self.tmask == self.tvalue,
            # does variable fulfill the conditions imposed by tvalue and tmask?
            z3_tnum_condition(variable, self.tvalue, self.tmask),
            # does variable fulfill the conditions of the bounds?
            self.lower <= variable,
            variable <= self.upper,
        )

def make_z3_intbounds_instance(name):
    variable = BitVec(name + "_concrete")
    tvalue = BitVec(name + "_tvalue")
    tmask = BitVec(name + "_tmask")
    upper = BitVec(name + "_upper")
    lower = BitVec(name + "_lower")
    return Z3IntBound(lower, upper, tvalue, tmask, variable)

def test_prove_invert():
    bound = make_z3_intbounds_instance('self')
    b2 = bound.invert_bound()
    prove_implies(
        bound.z3_formula(),
        b2.z3_formula(~bound.concrete_variable),
    )

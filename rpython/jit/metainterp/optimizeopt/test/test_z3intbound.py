""" The purpose of this test file is to do bounded model checking of the
IntBound methods with Z3.

The approach is to generate random bounds, then perform operations on them, and
ask Z3 whether the resulting bound is a sound approximation of the result.
"""

import pytest
import sys
import gc

from rpython.rlib.rarithmetic import LONG_BIT, r_uint, intmask, ovfcheck, uint_mul_high
from rpython.jit.metainterp.optimizeopt.intutils import (
    IntBound,
    unmask_one,
    unmask_zero,
    next_pow2_m1,
    lowest_set_bit_only,
    leading_zeros_mask,
    flip_msb,
    msbonly,
)
from rpython.jit.metainterp.optimize import InvalidLoop

from rpython.jit.metainterp.optimizeopt.test.test_intbound import knownbits_and_bound_with_contained_number

from rpython.jit.metainterp.optimizeopt.test.test_z3checktests import z3_pymod, z3_pydiv

try:
    import z3
    from hypothesis import given, strategies, assume, example
except ImportError:
    pytest.skip("please install z3 (z3-solver on pypi) and hypothesis")

def BitVecVal(value):
    return z3.BitVecVal(value, LONG_BIT)

def BitVec(name):
    return z3.BitVec(name, LONG_BIT)

def z3_with_reduced_bitwidth(width):
    def dec(test):
        assert test.func_name.endswith("logic") # doesn't work for code in intutils.py
        def newtest(*args, **kwargs):
            global LONG_BIT, MAXINT, MININT
            old_value = LONG_BIT
            LONG_BIT = width
            MAXINT = 2 ** (LONG_BIT - 1) - 1
            MININT = -2 ** (LONG_BIT - 1)
            try:
                return test(*args, **kwargs)
            finally:
                LONG_BIT = old_value
                MAXINT = sys.maxint
                MININT = -sys.maxint - 1
        return newtest
    return dec

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
        global model
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
    try:
        b3 = b1.mul_bound_no_overflow(b2)
    except InvalidLoop:
        assume(False)
    var1, formula1 = to_z3(b1)
    var2, formula2 = to_z3(b2)
    var3, formula3 = to_z3(b3, var1 * var2)
    m = z3.SignExt(LONG_BIT, var1) * z3.SignExt(LONG_BIT, var2)
    no_ovf = m == z3.SignExt(LONG_BIT, var1 * var2)
    prove_implies(formula1, formula2, no_ovf, formula3)

@given(bounds, bounds)
def test_tnum_mul(b1, b2):
    assume(not (b1._are_knownbits_implied() and b2._are_knownbits_implied()))
    tvalue, tmask = b1._tnum_mul(b2)
    b3 = IntBound.from_knownbits(tvalue, tmask)
    print b1, b2, b3
    var1, formula1 = to_z3(b1)
    var2, formula2 = to_z3(b2)
    var3, formula3 = to_z3(b3, var1 * var2)
    prove_implies(formula1, formula2, formula3)

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
def test_mod(b1, b2):
    b3 = b1.mod_bound(b2)
    print b1, b2, b3
    var1, formula1 = to_z3(b1)
    var2, formula2 = to_z3(b2)
    var3, nonzero = z3_pymod_nonzero(var1, var2)
    _, formula3 = to_z3(b3, var3)
    prove_implies(formula1, formula2, nonzero, formula3)


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
# precision

@given(bounds, bounds)
def dont_test_transfer_precision(b1, b2):
    # disabled, because it simply finds *a ton of* imprecision
    assume(not b1.is_constant())
    assume(not b2.is_constant())
    var1, formula1 = to_z3(b1)
    var2, formula2 = to_z3(b2)
    b3 = b1.add_bound(b2)
    ones = BitVec('ones')
    unknowns = BitVec('unknowns')
    lower = BitVec('lower')
    upper = BitVec('upper')
    solver = z3.Solver()
    solver.set("timeout", 5000)
    import gc
    gc.collect()
    print b1, b2, b3

    #res = solver.check(z3.And(
    #    ones & ~unknowns == ones,
    #    b3.tmask & ~unknowns != 0,
    #    z3.ForAll(
    #    [var1, var2],
    #    z3.Implies(
    #        z3.And(formula1, formula2),
    #        z3.And((var1 & var2) & ~unknowns == ones)))))
    #assert res == z3.unsat

    res = solver.check(z3.And(
        lower > b3.lower,
        z3.ForAll(
        [var1, var2],
        z3.Implies(
            z3.And(formula1, formula2),
            z3.And((var1 + var2) >= lower)))))
    assert res == z3.unsat

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
# explicit proofs of some of the helpers

def test_prove_next_pow2_m1():
    x = BitVec('x')
    res = next_pow2_m1(x)
    # it's a power of 2 - 1
    prove(res & (res + 1) == 0)
    # it's bigger than x
    prove(
        z3.BV2Int(res) + 1 >= z3.BV2Int(x)
    )

def test_prove_lowest_set_bit_only():
    x = BitVec('x')
    res = lowest_set_bit_only(x)
    prove_implies(
        x != 0,
        popcount64(res) == 1
    )
    prove_implies(
        x == 0,
        res == 0,
    )
    # do it the pedestrian way: if a bit is set, then the bits with lower
    # indexes must be 0
    conditions = []
    for i in range(LONG_BIT):
        for j in range(i):
            cond = z3.Implies(z3.Extract(i, i, res) == 1, z3.Extract(j, j, res) == 0)
            conditions.append(cond)

    prove(
        z3.And(*conditions)
    )

# ____________________________________________________________
# explicit proofs of IntBound logic/code

def make_z3_bound_and_tnum(name):
    """ make a z3 knownbits number and bounds.
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

def popcount64(w):
    w -= (w >> 1) & 0x5555555555555555
    w = (w & 0x3333333333333333) + ((w >> 2) & 0x3333333333333333)
    w = (w + (w >> 4)) & 0x0f0f0f0f0f0f0f0f
    return ((w * 0x0101010101010101) >> 56) & 0xff

def test_popcount64():
    assert popcount64(1 << 60) == 1
    assert popcount64((1 << 60) + 5) == 3
    assert popcount64((1 << 63) + 0b11010110111) == 9

def z3_add_overflow(a, b):
    result = a + b
    result_wide = z3.SignExt(LONG_BIT, a) + z3.SignExt(LONG_BIT, b)
    no_ovf = result_wide == z3.SignExt(LONG_BIT, result)
    return result, no_ovf

def z3_sub_overflow(a, b):
    result = a - b
    result_wide = z3.SignExt(LONG_BIT, a) - z3.SignExt(LONG_BIT, b)
    no_ovf = result_wide == z3.SignExt(LONG_BIT, result)
    return result, no_ovf

def z3_mul_overflow(a, b):
    result = a * b
    result_wide = z3.SignExt(LONG_BIT, a) * z3.SignExt(LONG_BIT, b)
    no_ovf = result_wide == z3.SignExt(LONG_BIT, result)
    return result, no_ovf

def z3_uint_mul_high(a, b):
    za = z3.ZeroExt(LONG_BIT, a)
    zb = z3.ZeroExt(LONG_BIT, b)
    return z3.Extract(LONG_BIT * 2 - 1, LONG_BIT, za * zb)


# debugging functions to understand the counterexamples

def s(p):
    if p.sort() == z3.BoolSort():
        print model.evaluate(p)
    else:
        print hex(model.evaluate(p).as_signed_long())

def u(p):
    print "r_uint(%s)" % bin(model.evaluate(p).as_long())

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

    @staticmethod
    def from_knownbits(tvalue, tmask):
        # compute lower and upper bound like shrinking does it
        res = Z3IntBound(None, None, tvalue, tmask)
        res.lower = res._get_minimum_signed_by_knownbits()
        res.upper = res._get_maximum_signed_by_knownbits()
        return res

    @staticmethod
    def intmask(x):
        # casts from unsigned to signed don't actually matter to Z3
        return x

    @staticmethod
    def r_uint(x):
        # casts from unsigned to signed don't actually matter to Z3
        return x

    @staticmethod
    def _add_check_overflow(a, b, default):
        result, no_ovf = z3_add_overflow(a, b)
        return z3.If(no_ovf, result, default)

    @staticmethod
    def _sub_check_overflow(a, b, default):
        result, no_ovf = z3_sub_overflow(a, b)
        return z3.If(no_ovf, result, default)

    @staticmethod
    def _urshift(a, b):
        return z3.LShR(a, b)

    def __repr__(self):
        more = ''
        if self.concrete_variable is not None:
            more = ', concrete_variable=%s' % (self.concrete_variable, )
        return "<Z3IntBound lower=%s, upper=%s, tvalue=%s, tmask=%s%s>" % (
            self.lower, self.upper, self.tvalue, self.tmask, more)
    __str__ = __repr__

    def z3_formula(self, variable=None, must_be_minimal=False):
        """ return the Z3 condition that:
        - self is well-formed
        - variable (or self.concrete_variable) is an element of the set
          described by self
        """
        if variable is None:
            variable = self.concrete_variable
            assert variable is not None
        result = z3.And(
            # is the tnum well-formed? ie are the unknown bits in tvalue set to 0?
            self.tvalue & ~self.tmask == self.tvalue,
            # does variable fulfill the conditions imposed by tvalue and tmask?
            z3_tnum_condition(variable, self.tvalue, self.tmask),
            # does variable fulfill the conditions of the bounds?
            self.lower <= variable,
            variable <= self.upper,
        )
        if must_be_minimal:
            tvalue, tmask, valid = self._tnum_improve_knownbits_by_bounds()
            result = z3.And(
                valid,
                self.tvalue == tvalue,
                self.tmask == tmask,
                result
            )
        return result

    def convert_to_concrete(self, model):
        """ A helper function that can be used to turn a Z3 counterexample into an
        IntBound instance to understand it better. """
        v = r_uint(model.evaluate(self.tvalue).as_long())
        m = r_uint(model.evaluate(self.tmask).as_long())
        l = model.evaluate(self.lower).as_signed_long()
        u = model.evaluate(self.upper).as_signed_long()
        return IntBound(l, u, v, m, do_shrinking=False)

    def prove_implies(self, *args):
        formula_args = [(arg.z3_formula() if isinstance(arg, Z3IntBound) else arg)
                        for arg in (self, ) + args]
        try:
            prove_implies(
                *formula_args,
                use_timeout=False
            )
        except CheckError as e:
            model = e.args[1]
            example_self = self.convert_to_concrete(model)
            print "ERROR", args
            print "COUNTEREXAMPLE", example_self
            assert 0

def make_z3_intbounds_instance(name, concrete_variable=None):
    if concrete_variable is None:
        variable = BitVec(name + "_concrete")
    else:
        variable = concrete_variable
    tvalue = BitVec(name + "_tvalue")
    tmask = BitVec(name + "_tmask")
    upper = BitVec(name + "_upper")
    lower = BitVec(name + "_lower")
    return Z3IntBound(lower, upper, tvalue, tmask, variable)

def test_prove_invert():
    bound = make_z3_intbounds_instance('self')
    b2 = bound.invert_bound()
    bound.prove_implies(
        b2.z3_formula(~bound.concrete_variable),
    )

def test_prove_min_max_unsigned_by_knownbits():
    bound = make_z3_intbounds_instance('self')
    minimum = bound.get_minimum_unsigned_by_knownbits()
    bound.prove_implies(
        z3.ULE(minimum, bound.concrete_variable),
    )
    maximum = bound.get_maximum_unsigned_by_knownbits()
    bound.prove_implies(
        z3.ULE(bound.concrete_variable, maximum),
    )

def test_prove_min_max_unsigned_logic():
    bound = make_z3_intbounds_instance('self')
    same_sign = ((bound.lower ^ bound.upper) >> (LONG_BIT - 1)) == 0
    lower = z3.If(same_sign, bound.lower, bound.get_minimum_unsigned_by_knownbits())
    upper = z3.If(same_sign, bound.upper, bound.get_maximum_unsigned_by_knownbits())
    bound.prove_implies(
        z3.ULE(lower, bound.concrete_variable)
    )
    bound.prove_implies(
        same_sign,
        z3.ULE(bound.concrete_variable, upper)
    )

def test_prove_min_max_signed_by_knownbits():
    bound = make_z3_intbounds_instance('self')
    minimum = bound._get_minimum_signed_by_knownbits()
    bound.prove_implies(
        minimum <= bound.concrete_variable
    )
    bound.prove_implies(
        z3_tnum_condition(minimum, bound.tvalue, bound.tmask),
    )

    maximum = bound._get_maximum_signed_by_knownbits()
    bound.prove_implies(
        bound.concrete_variable <= maximum,
    )
    bound.prove_implies(
        z3_tnum_condition(maximum, bound.tvalue, bound.tmask),
    )

def test_prove_or():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    b3 = b1.or_bound(b2)
    b3.concrete_variable = b1.concrete_variable | b2.concrete_variable
    b1.prove_implies(
        b2,
        b3
    )

def test_prove_or_bounds_implied_by_knownbits():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    b3 = b1.or_bound(b2)
    # similar to test_prove_xor_bounds_implied_by_knownbits, the following
    # logic was used to give explicit bounds for or of two nonnegative numbers.
    mostsignificant = b1.upper | b2.upper
    upper = next_pow2_m1(mostsignificant)
    result = b1.concrete_variable | b2.concrete_variable
    b1.prove_implies(
        b1.z3_formula(must_be_minimal=True),
        b2.z3_formula(must_be_minimal=True),
        b1.lower >= 0,
        b2.lower >= 0,
        z3.And(b3.upper <= upper, b3.lower >= 0),
    )

def test_prove_xor():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    b3 = b1.xor_bound(b2)
    b3.concrete_variable = b1.concrete_variable ^ b2.concrete_variable
    b1.prove_implies(
        b2,
        b3,
    )

def test_prove_xor_bounds_implied_by_knownbits():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')

    # for non-negative b1 and b2, xor_bound used to contain code that set the
    # lower bound to 0, and an upper bound to:
    mostsignificant = b1.upper | b2.upper
    upper = next_pow2_m1(mostsignificant)
    # this is unnecessary, because the information is implied by the knownbits,
    # which we prove here

    result = b1.concrete_variable ^ b2.concrete_variable

    b3 = b1.xor_bound(b2)
    b3.concrete_variable = result
    b1.prove_implies(
        b1.z3_formula(must_be_minimal=True),
        b2.z3_formula(must_be_minimal=True),
        b1.lower >= 0,
        b2.lower >= 0,
        # check that the maximum implied by the known bits is not worse than
        # the maximum computed by the expression above
        z3.And(b3.upper <= upper, b3.lower >= 0),
    )

def test_prove_and():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    tvalue, tmask = b1._tnum_and(b2)
    b1.prove_implies(
        b2,
        z3_tnum_condition(b1.concrete_variable & b2.concrete_variable, tvalue, tmask),
    )

def test_prove_and_bounds_logic():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    res = b1.concrete_variable & b2.concrete_variable
    b1.prove_implies(
        b2,
        z3.Or(b1.known_nonnegative(), b2.known_nonnegative()),
        res >= 0
    )
    b1.prove_implies(
        b2,
        b1.known_nonnegative(),
        res <= b1.upper,
    )
    b1.prove_implies(
        b2,
        b2.known_nonnegative(),
        res <= b2.upper,
    )

def test_prove_add_knownbits():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    result = b1.concrete_variable + b2.concrete_variable
    res_tvalue, res_tmask = b1._tnum_add(b2)
    b1.prove_implies(
        b2,
        z3_tnum_condition(result, res_tvalue, res_tmask),
    )

def test_prove_add_bound_logic():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    result = b1.concrete_variable + b2.concrete_variable
    lower, no_ovf_lower = z3_add_overflow(b1.lower, b2.lower)
    upper, no_ovf_upper = z3_add_overflow(b1.upper, b2.upper)
    result_lower = z3.If(z3.And(no_ovf_lower, no_ovf_upper),
                         lower, MININT)
    result_upper = z3.If(z3.And(no_ovf_lower, no_ovf_upper),
                         upper, MAXINT)
    tvalue, tmask = b1._tnum_add(b2)
    b3 = Z3IntBound(result_lower, result_upper, tvalue, tmask, result)
    b1.prove_implies(
        b2,
        b3
    )

def test_prove_add_bound_cannot_overflow_logic():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    result, no_ovf_result = z3_add_overflow(b1.concrete_variable, b2.concrete_variable)
    lower, no_ovf_lower = z3_add_overflow(b1.lower, b2.lower)
    upper, no_ovf_upper = z3_add_overflow(b1.upper, b2.upper)
    b1.prove_implies(
        b2,
        z3.And(no_ovf_lower, no_ovf_upper),
        no_ovf_result,
    )

def test_prove_add_bound_must_overflow_logic():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    result, no_ovf_result = z3_add_overflow(b1.concrete_variable, b2.concrete_variable)
    lower, no_ovf_lower = z3_add_overflow(b1.lower, b2.lower)
    upper, no_ovf_upper = z3_add_overflow(b1.upper, b2.upper)
    same_sign_b1 = ((b1.lower ^ b1.upper) >> (LONG_BIT - 1)) == 0
    same_sign_b2 = ((b2.lower ^ b2.upper) >> (LONG_BIT - 1)) == 0
    b1.prove_implies(
        b2,
        z3.And(z3.Or(same_sign_b1, same_sign_b2), z3.Not(no_ovf_lower), z3.Not(no_ovf_upper)),
        z3.Not(no_ovf_result),
    )

def test_prove_add_bound_no_overflow():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    result, no_ovf = z3_add_overflow(b1.concrete_variable, b2.concrete_variable)
    b3 = b1.add_bound_no_overflow(b2)
    b1.prove_implies(
        b2,
        no_ovf,
        b3.z3_formula(result)
    )

def test_prove_add_bound_no_overflow_backwards_is_sub_bound_no_overflow():
    # situation:
    # i3 = int_add_ovf(i1, i2)
    # guard_no_overflow()
    # the fact that the addition didn't overflow can be used to infer something
    # about i1 and i2 as well, namely:
    # i1 = int_sub_ovf(i3, i2)
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    result, no_ovf = z3_add_overflow(b1.concrete_variable, b2.concrete_variable)
    b3 = b1.add_bound_no_overflow(b2)
    b1better = b3.sub_bound_no_overflow(b2)
    b1.prove_implies(
        b2,
        no_ovf,
        b1better.z3_formula(b1.concrete_variable)
    )

def test_prove_sub_bound_no_overflow_backwards():
    # situation:
    # i3 = int_sub_ovf(i1, i2)
    # guard_no_overflow()
    # the fact that the subtraction didn't overflow can be used to infer something
    # about i1 and i2 as well, namely:
    # i1 = int_add_ovf(i2, i3)
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    result, no_ovf = z3_sub_overflow(b1.concrete_variable, b2.concrete_variable)
    b3 = b1.sub_bound_no_overflow(b2)
    b1better = b2.add_bound_no_overflow(b3)
    b1.prove_implies(
        b2,
        no_ovf,
        b1better.z3_formula(b1.concrete_variable)
    )
    # for i2, we can use sub_bound_no_overflow:
    # i2 = int_sub_ovf(i1, i3)
    b2better = b1.sub_bound_no_overflow(b3)
    b1.prove_implies(
        b2,
        no_ovf,
        b2better.z3_formula(b2.concrete_variable)
    )

def test_prove_neg_logic():
    b1 = make_z3_intbounds_instance('self')
    one = Z3IntBound(BitVecVal(1), BitVecVal(1), BitVecVal(1), BitVecVal(0))
    b2 = b1.invert_bound()
    tvalue, tmask = b2._tnum_add(one) # constant 1
    result = -b1.concrete_variable
    b1.prove_implies(
        z3_tnum_condition(result, tvalue, tmask)
    )

def test_prove_sub_knownbits():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    result = b1.concrete_variable - b2.concrete_variable
    res_tvalue, res_tmask = b1._tnum_sub(b2)
    b1.prove_implies(
        b2,
        z3_tnum_condition(result, res_tvalue, res_tmask),
    )

def test_prove_sub_bound_logic():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    result = b1.concrete_variable - b2.concrete_variable
    lower, no_ovf_lower = z3_sub_overflow(b1.lower, b2.upper)
    upper, no_ovf_upper = z3_sub_overflow(b1.upper, b2.lower)
    result_lower = z3.If(z3.And(no_ovf_lower, no_ovf_upper),
                         lower, MININT)
    result_upper = z3.If(z3.And(no_ovf_lower, no_ovf_upper),
                         upper, MAXINT)
    tvalue, tmask = b1._tnum_sub(b2)
    b3 = Z3IntBound(result_lower, result_upper, tvalue, tmask, result)
    b1.prove_implies(
        b2,
        b3
    )

def test_prove_sub_bound_cannot_overflow_logic():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    result, no_ovf_result = z3_sub_overflow(b1.concrete_variable, b2.concrete_variable)
    lower, no_ovf_lower = z3_sub_overflow(b1.lower, b2.upper)
    upper, no_ovf_upper = z3_sub_overflow(b1.upper, b2.lower)
    b1.prove_implies(
        b2,
        z3.And(no_ovf_lower, no_ovf_upper),
        no_ovf_result,
    )

def test_prove_sub_bound_no_overflow():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    result, no_ovf = z3_sub_overflow(b1.concrete_variable, b2.concrete_variable)
    b3 = b1.sub_bound_no_overflow(b2)
    b1.prove_implies(
        b2,
        no_ovf,
        b3.z3_formula(result)
    )

def test_prove_sub_bound_must_overflow_logic():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    result, no_ovf_result = z3_sub_overflow(b1.concrete_variable, b2.concrete_variable)
    lower, no_ovf_lower = z3_sub_overflow(b1.lower, b2.upper)
    upper, no_ovf_upper = z3_sub_overflow(b1.upper, b2.lower)
    same_sign_b1 = ((b1.lower ^ b1.upper) >> (LONG_BIT - 1)) == 0
    same_sign_b2 = ((b2.lower ^ b2.upper) >> (LONG_BIT - 1)) == 0
    b1.prove_implies(
        b2,
        z3.And(z3.Or(same_sign_b1, same_sign_b2), z3.Not(no_ovf_lower), z3.Not(no_ovf_upper)),
        z3.Not(no_ovf_result),
    )


def test_prove_and_backwards():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    b3 = make_z3_intbounds_instance('result')
    res = b1.concrete_variable & b2.concrete_variable
    b3.concrete_variable = res
    better_tvalue, better_tmask, valid = b2._tnum_and_backwards(b3)
    b1.prove_implies(
        b2,
        b3,
        z3.And(
            valid,
            z3_tnum_condition(b1.concrete_variable, better_tvalue, better_tmask)
        ),
    )

def test_prove_and_backwards_inconsistent():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    b3 = make_z3_intbounds_instance('result')
    res = b1.concrete_variable & b2.concrete_variable
    better_tvalue, better_tmask, valid = b2._tnum_and_backwards(b3)
    # hm, this is just the contraposition of test_prove_and_backwards, so
    # trivially true?
    b1.prove_implies(
        b2,
        b3,
        # if we aren't consistent
        z3.Not(valid),
        # then the result must be different than the result of the &
        b3.concrete_variable != res
    )

def test_prove_or_backwards():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    b3 = make_z3_intbounds_instance('result')
    res = b1.concrete_variable | b2.concrete_variable
    b3.concrete_variable = res
    better_tvalue, better_tmask, valid = b2._tnum_or_backwards(b3)
    b1.prove_implies(
        b2,
        b3,
        z3.And(
            valid,
            z3_tnum_condition(b1.concrete_variable, better_tvalue, better_tmask)
        ),
    )

def test_prove_known_unsigned_lt_logic():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    max_self = b1.get_maximum_unsigned_by_knownbits()
    min_other = b2.get_minimum_unsigned_by_knownbits()
    b1.prove_implies(
        b2,
        z3.ULT(max_self, min_other),
        z3.ULT(b1.concrete_variable, b2.concrete_variable),
    )

def test_prove_known_unsigned_lt_from_signed_lt_logic():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    b1.prove_implies(
        b2,
        b1.lower >= 0,
        b2.lower < b2.lower,
        z3.ULT(b1.concrete_variable, b2.concrete_variable),
    )
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    b1.prove_implies(
        b2,
        b1.lower < 0,
        b2.lower < b2.lower,
        z3.ULT(b1.concrete_variable, b2.concrete_variable),
    )

def test_prove_uint_less_nonnegative_implies_nonnegative():
    index = BitVec('index')
    length = BitVec('length')
    prove_implies(
        length >= 0,
        z3.ULT(index, length),
        z3.And(index >= 0, index < length),
    )
    prove_implies(
        length >= 0,
        z3.ULT(index, length),
        z3.And(index >= 0, index <= length - 1),
    )
    prove_implies(
        length >= 0,
        z3.ULE(index, length),
        z3.And(index >= 0, index <= length),
    )

def test_prove_uint_greater_negative_implies_negative():
    a = BitVec('a')
    b = BitVec('b')
    prove_implies(
        b < 0,
        z3.UGE(a, b),
        z3.And(a < 0, a >= b),
    )
    prove_implies(
        b < 0,
        z3.UGT(a, b),
        z3.And(a < 0, a > b),
    )
    # an example
    prove_implies(
        b <= -3,
        b >= -4,
        z3.UGT(a, b),
        z3.And(a <= -1, a >= -3),
    )


def test_prove_known_cmp():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    b1.prove_implies(
        b2,
        b1.known_lt(b2),
        b1.concrete_variable < b2.concrete_variable,
    )
    b1.prove_implies(
        b2,
        b1.known_le(b2),
        b1.concrete_variable <= b2.concrete_variable,
    )
    b1.prove_implies(
        b2,
        b1.known_gt(b2),
        b1.concrete_variable > b2.concrete_variable,
    )
    b1.prove_implies(
        b2,
        b1.known_ge(b2),
        b1.concrete_variable >= b2.concrete_variable,
    )

def test_prove_tnum_intersect():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    tvalue, tmask, valid = b1._tnum_intersect(b2.tvalue, b2.tmask)
    b1.prove_implies(
        b2.z3_formula(b1.concrete_variable),
        z3.And(
            valid,
            z3_tnum_condition(b1.concrete_variable, tvalue, tmask)
        )
    )
    # check that if valid if false, there are no values in the intersection
    b1.prove_implies(
        z3.Not(valid),
        z3.Not(b2.z3_formula(b1.concrete_variable)),
    )
    # and also that we only gain information
    b1.prove_implies(
        b2.z3_formula(b1.concrete_variable),
        valid,
        popcount64(~tmask) >= popcount64(~b1.tmask),
    )

def test_prove_tnum_intersect_idempotent():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    b2.concrete_variable = b1.concrete_variable
    tvalue1, tmask1, valid1 = b1._tnum_intersect(b2.tvalue, b2.tmask)
    tvalue2, tmask2, valid2 = b1._tnum_intersect(tvalue1, tmask1)
    b1.prove_implies(
        b2,
        z3.And(
            tvalue1 == tvalue2,
            tmask1 == tmask2,
            valid1,
            valid2,
        )
    )


# ____________________________________________________________
# prove things about _shrink_knownbits_by_bounds

def test_prove_tnum_implied_by_bounds():
    self = make_z3_intbounds_instance('self')
    bounds_tvalue, bounds_tmask = self._tnum_implied_by_bounds()
    val = BitVec('val')
    self.prove_implies(
        val >= self.lower,
        val <= self.upper,
        z3_tnum_condition(val, bounds_tvalue, bounds_tmask)
    )

def test_prove_shrink_knownbits_by_bounds():
    self = make_z3_intbounds_instance('self')
    tvalue, tmask, valid = self._tnum_improve_knownbits_by_bounds()
    self.prove_implies(
        z3_tnum_condition(self.concrete_variable, self.tvalue, self.tmask),
        z3.And(valid, z3_tnum_condition(self.concrete_variable, tvalue, tmask)),
    )

# ____________________________________________________________
# prove things about _shrink_bounds_by_knownbits

def test_prove_shrink_bounds_by_knownbits_min_case1():
    # case 1, cl2set > set2cl
    b1 = make_z3_intbounds_instance('self')

    threshold = b1.lower
    working_min, cl2set, set2cl = b1._helper_min_max_prepare(threshold)
    new_threshold = b1._helper_min_case1(working_min, cl2set)

    # show that the new_threshold is larger than threshold
    b1.prove_implies(
        b1._get_minimum_signed_by_knownbits() < threshold,
        working_min != threshold,
        z3.UGT(cl2set, set2cl),
        new_threshold > threshold,
    )
    # correctness: show that there are no elements x in b1 with
    # threshold <= x < new_threshold
    b1.prove_implies(
        b1._get_minimum_signed_by_knownbits() < threshold,
        working_min != threshold,
        z3.UGT(cl2set, set2cl),
        z3.Not(b1.concrete_variable < new_threshold),
    )
    # precision: new_threshold is an element in the set, ie we
    # couldn't have increased the bound further
    b1.prove_implies(
        b1._get_minimum_signed_by_knownbits() < threshold,
        working_min != threshold,
        z3.UGT(cl2set, set2cl),
        z3_tnum_condition(new_threshold, b1.tvalue, b1.tmask),
    )


def test_prove_shrink_bounds_by_knownbits_correctness_min_case2():
    # case 2) cl2set <= set2cl
    b1 = make_z3_intbounds_instance('self')

    threshold = b1.lower
    working_min, cl2set, set2cl = b1._helper_min_max_prepare(threshold)
    working_min_ne_threshold = working_min != threshold

    new_threshold = b1._helper_min_case2(working_min, set2cl)

    # check that the bound is not getting worse
    b1.prove_implies(
        b1._get_minimum_signed_by_knownbits() < threshold,
        working_min_ne_threshold,
        z3.ULE(cl2set, set2cl),
        new_threshold > threshold
    )

    # correctness: show that there are no elements x in b1 with
    # threshold <= x < new_threshold
    b1.prove_implies(
        b1._get_minimum_signed_by_knownbits() < threshold,
        working_min_ne_threshold,
        z3.ULE(cl2set, set2cl),
        z3.Not(b1.concrete_variable < new_threshold),
    )

    # precision: new_threshold is an element in the set, ie we
    # couldn't have increased the bound further
    b1.prove_implies(
        b1._get_minimum_signed_by_knownbits() < threshold,
        working_min_ne_threshold,
        z3.ULE(cl2set, set2cl),
        z3_tnum_condition(new_threshold, b1.tvalue, b1.tmask),
    )

def test_prove_shrink_bounds_by_knownbits_max_case1():
    # case 1, cl2set < set2cl
    b1 = make_z3_intbounds_instance('self')

    threshold = b1.upper
    working_min, cl2set, set2cl = b1._helper_min_max_prepare(threshold)
    new_threshold = b1._helper_max_case1(working_min, set2cl)

    # show that the new_threshold is smaller than threshold
    b1.prove_implies(
        b1._get_maximum_signed_by_knownbits() > threshold,
        working_min != threshold,
        z3.ULT(cl2set, set2cl),
        new_threshold < threshold,
    )
    # correctness: show that there are no elements x in b1 with
    # new_threshold <= x < threshold
    b1.prove_implies(
        b1._get_maximum_signed_by_knownbits() > threshold,
        working_min != threshold,
        z3.ULT(cl2set, set2cl),
        z3.Not(b1.concrete_variable > new_threshold),
    )
    # precision: new_threshold is an element in the set, ie we
    # couldn't have increased the bound further
    b1.prove_implies(
        b1._get_maximum_signed_by_knownbits() > threshold,
        working_min != threshold,
        z3.ULT(cl2set, set2cl),
        z3_tnum_condition(new_threshold, b1.tvalue, b1.tmask),
    )


def test_prove_shrink_bounds_by_knownbits_correctness_max_case2():
    # case 2) cl2set >= set2cl
    b1 = make_z3_intbounds_instance('self')

    threshold = b1.upper
    working_max, cl2set, set2cl = b1._helper_min_max_prepare(threshold)
    working_max_ne_threshold = working_max != threshold

    new_threshold = b1._helper_max_case2(working_max, cl2set)

    # check that the bound is not getting worse
    b1.prove_implies(
        b1._get_maximum_signed_by_knownbits() > threshold,
        working_max_ne_threshold,
        z3.UGE(cl2set, set2cl),
        new_threshold < threshold
    )

    # correctness: show that there are no elements x in b1 with
    # threshold <= x < new_threshold
    b1.prove_implies(
        b1._get_maximum_signed_by_knownbits() > threshold,
        working_max_ne_threshold,
        z3.UGE(cl2set, set2cl),
        z3.Not(b1.concrete_variable > new_threshold),
    )

    # precision: new_threshold is an element in the set, ie we
    # couldn't have increased the bound further
    b1.prove_implies(
        b1._get_maximum_signed_by_knownbits() > threshold,
        working_max_ne_threshold,
        z3.UGE(cl2set, set2cl),
        z3_tnum_condition(new_threshold, b1.tvalue, b1.tmask),
    )

# ____________________________________________________________

def z3_lshift_overflow(a, b):
    res = a << b
    return res, (res >> b) == a

def z3_min(*args):
    res = args[0]
    for x in args[1:]:
        res = z3.If(res < x, res, x)
    return res

def z3_max(*args):
    res = args[0]
    for x in args[1:]:
        res = z3.If(res > x, res, x)
    return res

@z3_with_reduced_bitwidth(16)
def test_prove_lshift_bound_logic():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    # bounds logic
    result, no_ovf = z3_lshift_overflow(b1.concrete_variable, b2.concrete_variable)
    result1, no_ovf1 = z3_lshift_overflow(b1.lower, b2.lower)
    result2, no_ovf2 = z3_lshift_overflow(b1.lower, b2.upper)
    result3, no_ovf3 = z3_lshift_overflow(b1.upper, b2.lower)
    result4, no_ovf4 = z3_lshift_overflow(b1.upper, b2.upper)
    min1 = z3_min(result1, result2, result3, result4)
    max1 = z3_max(result1, result2, result3, result4)
    b1.prove_implies(
        b2,
        z3.And(no_ovf1, no_ovf2, no_ovf3, no_ovf4),
        z3.And(min1 <= result, result <= max1, no_ovf),
    )

def test_prove_lshift_knownbits():
    b1 = make_z3_intbounds_instance('self')
    c = BitVec('const')
    result = b1.concrete_variable << c
    tvalue, tmask = b1._tnum_lshift(c)
    b1.prove_implies(
        c >= 0,
        c < LONG_BIT,
        z3_tnum_condition(result, tvalue, tmask)
    )

def test_prove_lshift_bound_cannot_overflow_logic():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    result, no_ovf = z3_lshift_overflow(b1.concrete_variable, b2.concrete_variable)
    _, no_ovf1 = z3_lshift_overflow(b1.lower, b2.lower)
    _, no_ovf2 = z3_lshift_overflow(b1.lower, b2.upper)
    _, no_ovf3 = z3_lshift_overflow(b1.upper, b2.lower)
    _, no_ovf4 = z3_lshift_overflow(b1.upper, b2.upper)
    b1.prove_implies(
        b2,
        z3.And(no_ovf1, no_ovf2, no_ovf3, no_ovf4),
        no_ovf
    )

def test_prove_rshift_knownbits():
    b1 = make_z3_intbounds_instance('self')
    c = BitVec('const')
    result = b1.concrete_variable >> c
    tvalue, tmask = b1._tnum_rshift(c)
    b1.prove_implies(
        c >= 0,
        z3_tnum_condition(result, tvalue, tmask),
    )

def test_prove_rshift_bound_logic():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    # bounds logic
    result = b1.concrete_variable >> b2.concrete_variable
    result1 = b1.lower >> b2.lower
    result2 = b1.lower >> b2.upper
    result3 = b1.upper >> b2.lower
    result4 = b1.upper >> b2.upper
    min1 = z3_min(result1, result2, result3, result4)
    max1 = z3_max(result1, result2, result3, result4)
    b1.prove_implies(
        b2,
        b2.lower >= 0,
        min1 <= result,
        result <= max1,
    )

def test_prove_urshift_knownbits():
    b1 = make_z3_intbounds_instance('self')
    c = BitVec('const')
    result = z3.LShR(b1.concrete_variable, c)
    tvalue, tmask = b1._tnum_urshift(c)
    b1.prove_implies(
        c >= 0,
        z3_tnum_condition(result, tvalue, tmask),
    )

def test_prove_lshift_bound_backwards_logic():
    b1 = make_z3_intbounds_instance('self')
    c_other = BitVec('const')
    res = b1.concrete_variable << c_other
    bresult = make_z3_intbounds_instance('result', res)
    tvalue = z3.LShR(bresult.tvalue, c_other)
    tmask = z3.LShR(bresult.tmask, c_other)
    s_tmask = ~z3.LShR(-1, c_other)
    valid = (bresult.tvalue & ((1 << c_other) - 1)) == 0
    tmask |= s_tmask
    b1.prove_implies(
        bresult,
        0 <= c_other,
        c_other <= LONG_BIT,
        z3.And(
            valid,
            z3_tnum_condition(b1.concrete_variable, tvalue, tmask)
        ),
    )

def test_prove_rshift_bound_backwards_logic():
    b1 = make_z3_intbounds_instance('self')
    c_other = BitVec('const')
    res = b1.concrete_variable >> c_other
    bresult = make_z3_intbounds_instance('result', res)
    tvalue = bresult.tvalue << c_other
    tmask = bresult.tmask << c_other
    tmask |= (1 << c_other) - 1
    b1.prove_implies(
        bresult,
        0 <= c_other,
        c_other <= LONG_BIT,
        z3_tnum_condition(b1.concrete_variable, tvalue, tmask)
    )

@z3_with_reduced_bitwidth(8)
def test_prove_mul_bound_logic():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    result, no_ovf = z3_mul_overflow(b1.concrete_variable, b2.concrete_variable)
    result1, no_ovf1 = z3_mul_overflow(b1.lower, b2.lower)
    result2, no_ovf2 = z3_mul_overflow(b1.lower, b2.upper)
    result3, no_ovf3 = z3_mul_overflow(b1.upper, b2.lower)
    result4, no_ovf4 = z3_mul_overflow(b1.upper, b2.upper)
    min1 = z3_min(result1, result2, result3, result4)
    max1 = z3_max(result1, result2, result3, result4)
    b1.prove_implies(
        b2,
        z3.And(no_ovf1, no_ovf2, no_ovf3, no_ovf4),
        z3.And(min1 <= result, result <= max1, no_ovf),
    )

@z3_with_reduced_bitwidth(8)
def test_prove_mul_bound_cannot_overflow_logic():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    result, no_ovf_result = z3_mul_overflow(b1.concrete_variable, b2.concrete_variable)
    result1, no_ovf1 = z3_mul_overflow(b1.lower, b2.lower)
    result2, no_ovf2 = z3_mul_overflow(b1.lower, b2.upper)
    result3, no_ovf3 = z3_mul_overflow(b1.upper, b2.lower)
    result4, no_ovf4 = z3_mul_overflow(b1.upper, b2.upper)
    b1.prove_implies(
        b2,
        z3.And(no_ovf1, no_ovf2, no_ovf3, no_ovf4),
        no_ovf_result,
    )

@z3_with_reduced_bitwidth(8)
def test_prove_mul_bound_no_overflow_logic():
    def saturating_mul(a, b):
        result, no_ovf = z3_mul_overflow(a, b)
        same_sign = ((a ^ b) >> (LONG_BIT - 1)) == 0
        default = z3.If(same_sign, a - a + MAXINT, a - a + MININT)
        return z3.If(no_ovf, result, default)
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    result, no_ovf = z3_mul_overflow(b1.concrete_variable, b2.concrete_variable)
    result1 = saturating_mul(b1.lower, b2.lower)
    result2 = saturating_mul(b1.lower, b2.upper)
    result3 = saturating_mul(b1.upper, b2.lower)
    result4 = saturating_mul(b1.upper, b2.upper)
    min1 = z3_min(result1, result2, result3, result4)
    max1 = z3_max(result1, result2, result3, result4)
    b1.prove_implies(
        b2,
        no_ovf,
        z3.And(min1 <= result, result <= max1),
    )

@z3_with_reduced_bitwidth(8)
def test_prove_mul_bound_must_overflow_logic():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    result, no_ovf_result = z3_mul_overflow(b1.concrete_variable, b2.concrete_variable)
    lower, no_ovf_lower = z3_mul_overflow(b1.lower, b2.lower)
    upper, no_ovf_upper = z3_mul_overflow(b1.upper, b2.upper)
    b1.prove_implies(
        b2,
        b1.lower > 0,
        b2.lower > 0,
        z3.Not(no_ovf_lower),
        z3.Not(no_ovf_result),
    )
    b1.prove_implies(
        b2,
        b1.upper < 0,
        b2.upper < 0,
        z3.Not(no_ovf_upper),
        z3.Not(no_ovf_result),
    )

    _, no_ovf_upper_lower = z3_mul_overflow(b1.upper, b2.lower)
    b1.prove_implies(
        b2,
        b1.upper < 0,
        b2.lower > 0,
        z3.Not(no_ovf_upper_lower),
        z3.Not(no_ovf_result),
    )

def z3_pymod_nonzero(x, y):
    r = x % y
    res = r + (y & z3.If(y < 0, -r, r) >> (LONG_BIT - 1))
    return res, y != 0

@z3_with_reduced_bitwidth(16)
def test_prove_mod_bound_logic():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    result, nonzero = z3_pymod_nonzero(b1.concrete_variable, b2.concrete_variable)
    b1.prove_implies(
        b2,
        nonzero,
        z3.And(result <= z3_max(b2.upper - 1, 0), z3_min(b2.lower + 1, 0) <= result)
    )

def z3_pydiv_nonzero_ovf(x, y):
    r = x / y
    psubx = r * y - x
    res = r + (z3.If(y < 0, psubx, -psubx) >> (LONG_BIT - 1))
    no_ovf = z3.Not(z3.And(x == MININT, y == -1))
    return res, y != 0, no_ovf


@z3_with_reduced_bitwidth(8)
def test_prove_div_bound_logic():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    result, nonzero, no_ovf = z3_pydiv_nonzero_ovf(b1.concrete_variable, b2.concrete_variable)
    result1, _, no_ovf1 = z3_pydiv_nonzero_ovf(b1.lower, b2.lower)
    result2, _, no_ovf2 = z3_pydiv_nonzero_ovf(b1.lower, b2.upper)
    result3, _, no_ovf3 = z3_pydiv_nonzero_ovf(b1.upper, b2.lower)
    result4, _, no_ovf4 = z3_pydiv_nonzero_ovf(b1.upper, b2.upper)
    min1 = z3_min(result1, result2, result3, result4)
    max1 = z3_max(result1, result2, result3, result4)
    b1.prove_implies(
        b2,
        nonzero,
        no_ovf1,
        no_ovf2,
        no_ovf3,
        no_ovf4,
        z3.Not(z3.And(b2.lower <= 0, 0 <= b2.upper)),
        z3.And(min1 <= result, result <= max1)
    )

def z3_tnum_mul(self, other):
    p, q = self, other
    acc_v = p.tvalue * q.tvalue
    acc_m = self.from_constant(0)
    for i in range(LONG_BIT):
        add_tmask = z3.If(
            z3.And(p.tvalue & 1 == 1, p.tmask & 1 == 0),
            q.tmask,
            z3.If(p.tmask & 1 == 1,
                  q.tvalue | q.tmask,
                  self.r_uint(0)))
        acc_m = self.from_knownbits(*acc_m._tnum_add(self.from_knownbits(self.r_uint(0), add_tmask)))
        p = self.from_knownbits(*p._tnum_urshift(1))
        q = self.from_knownbits(*q._tnum_lshift(1))
    return self.from_knownbits(acc_v, r_uint(0))._tnum_add(acc_m)

@z3_with_reduced_bitwidth(8)
def test_prove_mul_tnum_logic():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    result = b1.concrete_variable * b2.concrete_variable
    tvalue, tmask = z3_tnum_mul(b1, b2)
    b1.prove_implies(
        b2,
        z3.And(z3_tnum_condition(result, tvalue, tmask))
    )

def z3_uint_min(*args):
    res = args[0]
    for x in args[1:]:
        res = z3.If(z3.ULT(res, x), res, x)
    return res

def z3_uint_max(*args):
    res = args[0]
    for x in args[1:]:
        res = z3.If(z3.UGT(res, x), res, x)
    return res

@z3_with_reduced_bitwidth(6)
def test_prove_uint_mul_high_bounds_logic():
    def umin(bound):
        same_sign = ((bound.lower ^ bound.upper) >> (LONG_BIT - 1)) == 0
        return z3.If(same_sign, bound.lower, bound.get_minimum_unsigned_by_knownbits())
    def umax(bound):
        same_sign = ((bound.lower ^ bound.upper) >> (LONG_BIT - 1)) == 0
        return z3.If(same_sign, bound.upper, bound.get_maximum_unsigned_by_knownbits())
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    result = z3_uint_mul_high(b1.concrete_variable, b2.concrete_variable)
    r1 = z3_uint_mul_high(umin(b1), umin(b2))
    r2 = z3_uint_mul_high(umin(b1), umax(b2))
    r3 = z3_uint_mul_high(umax(b1), umin(b2))
    r4 = z3_uint_mul_high(umax(b1), umax(b2))
    b1.prove_implies(
        b2,
        z3.And(z3.UGE(result, z3_uint_min(r1, r2, r3, r4)), z3.ULE(result, z3_uint_max(r1, r2, r3, r4)))
    )

def test_prove_from_unsigned_bounds_logic():
    concrete = BitVec('concrete')
    ulower = BitVec('ulower')
    uupper = BitVec('uupper')
    same_sign = ((ulower ^ uupper) >> (LONG_BIT - 1)) == 0
    prove_implies(
        z3.ULE(ulower, concrete),
        z3.ULE(concrete, uupper),
        same_sign,
        ulower <= concrete,
        concrete <= uupper,
    )

# ____________________________________________________________
# proofs for rewrite rules

def test_int_xor_neg_one_is_invert():
    x = BitVec('x')
    prove(x ^ -1 == ~x)

def test_uint_cmp_equivalent_int_cmp_if_same_sign():
    x = BitVec('x')
    y = BitVec('y')
    prove_implies(
        (x >= 0) == (y >= 0),
        z3.ULT(x, y) == (x < y),
    )
    prove_implies(
        (x >= 0) == (y >= 0),
        z3.ULE(x, y) == (x <= y),
    )
    prove_implies(
        (x >= 0) == (y >= 0),
        z3.UGT(x, y) == (x > y),
    )
    prove_implies(
        (x >= 0) == (y >= 0),
        z3.UGE(x, y) == (x >= y),
    )

def test_prove_int_mul_1_lshift_rewrite():
    x = BitVec('x')
    y = BitVec('y')
    prove_implies(
        0 <= y,
        y < LONG_BIT,
        x * (1 << y) == x << y
    )

def test_prove_uint_mul_high_pow_2():
    # idea for a uint_mul_high optimization that would help pydrofoil
    x = BitVec('x')
    y = BitVec('y')
    prove_implies(
        0 <= y,
        y < LONG_BIT - 2,
        z3_uint_mul_high(x, 1 << y) == z3.LShR(x, LONG_BIT - y)
    )

def test_prove_uint_gt_zero_is_int_is_true():
    x = BitVec('x')
    prove_implies(
        z3.UGT(x, 0),
        x != 0,
    )

def test_prove_uint_ge_one_is_int_is_true():
    x = BitVec('x')
    prove_implies(
        z3.UGE(x, 1),
        x != 0,
    )

def test_prove_shift_back_and_forth_is_mask():
    x = BitVec('x')
    y = BitVec('y')
    prove_implies(
        y >= 0,
        y < LONG_BIT,
        (x >> y) << y == x & (-1 << y)
    )
    prove_implies(
        y >= 0,
        y < LONG_BIT,
        z3.LShR(x, y) << y == x & (-1 << y)
    )
    prove_implies(
        y >= 0,
        y < LONG_BIT,
        z3.LShR(x << y, y) == x & z3.LShR(-1, y)
    )

def test_prove_int_xor_int_xor_const():
    x = BitVec('x')
    c = BitVec('c')
    prove(
        x ^ (x ^ c) == c
    )

def test_prove_int_and_is_associative():
    x = BitVec('x')
    c1 = BitVec('c1')
    c2 = BitVec('c2')
    prove(
        (x & c1) & c2 == x & (c1 & c2)
    )

def test_prove_int_and_with_itself():
    x = BitVec('x')
    prove(
        x & x == x
    )

def test_prove_condition_and_mask_useless():
    b0 = make_z3_intbounds_instance('self')
    b1 = make_z3_intbounds_instance('other')
    x = b0.concrete_variable
    y = b1.concrete_variable
    b0.prove_implies(
        b1,
        ~b1.tvalue & (b0.tmask | b0.tvalue) == 0,
        x & y == x
    )

def test_prove_condition_xor_is_or_is_add():
    b0 = make_z3_intbounds_instance('self')
    b1 = make_z3_intbounds_instance('other')
    x = b0.concrete_variable
    y = b1.concrete_variable
    tvalue, tmask = b0._tnum_and(b1)
    # x + y = x ^ y + (x & y) * 2
    # therefore if x & y is known 0, then x + y == x ^ y
    b0.prove_implies(
        b1,
        tvalue | tmask == 0,
        z3.And(x ^ y == x + y, x | y == x + y)
    )

def test_prove_uint_ge_zero_is_int_is_true():
    x = BitVec('x')
    prove(
        z3.UGE(0, x) == (x == 0)
    )
    prove(
        z3.ULE(x, 0) == (x == 0)
    )

def test_prove_int_sub_int_eq_const():
    x = BitVec('x')
    c = BitVec('c')
    TRUEBV = z3.BitVecVal(1, LONG_BIT)
    FALSEBV = z3.BitVecVal(0, LONG_BIT)
    prove(
        (x - z3.If(x == c, TRUEBV, FALSEBV)) != c
    )

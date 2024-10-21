""" The purpose of this test file is to do bounded model checking of the
IntBound methods with Z3.

The approach is to generate random bounds, then perform operations on them, and
ask Z3 whether the resulting bound is a sound approximation of the result.
"""

import pytest
import sys
import gc

from rpython.rlib.rarithmetic import LONG_BIT, r_uint, intmask, ovfcheck
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
            global LONG_BIT
            old_value = LONG_BIT
            LONG_BIT = width
            try:
                return test(*args, **kwargs)
            finally:
                LONG_BIT = old_value
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
    def from_constant(const):
        if isinstance(const, int):
            const = BitVecVal(const)
        res = Z3IntBound(const, const, const, 0)
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

    # ____________________________________________________________
    # reimplementations of methods with control flow that Z3 doesn't support

    def add_bound(self, other):
        lower, no_ovf_lower = z3_add_overflow(self.lower, other.lower)
        upper, no_ovf_upper = z3_add_overflow(self.upper, other.upper)
        result_lower = z3.If(z3.And(no_ovf_lower, no_ovf_upper),
                             lower, MININT)
        result_upper = z3.If(z3.And(no_ovf_lower, no_ovf_upper),
                             upper, MAXINT)
        tvalue, tmask = self._tnum_add(other)
        return Z3IntBound(result_lower, result_upper, tvalue, tmask)

    def sub_bound(self, other):
        result = self.concrete_variable - other.concrete_variable
        lower, no_ovf_lower = z3_sub_overflow(self.lower, other.upper)
        upper, no_ovf_upper = z3_sub_overflow(self.upper, other.lower)
        result_lower = z3.If(z3.And(no_ovf_lower, no_ovf_upper),
                             lower, MININT)
        result_upper = z3.If(z3.And(no_ovf_lower, no_ovf_upper),
                             upper, MAXINT)
        tvalue, tmask = self._tnum_sub(other)
        return Z3IntBound(result_lower, result_upper, tvalue, tmask)

    def add_bound_cannot_overflow(self, other):
        lower, no_ovf_lower = z3_add_overflow(self.lower, other.lower)
        upper, no_ovf_upper = z3_add_overflow(self.upper, other.upper)
        return z3.And(no_ovf_lower, no_ovf_upper)

    def sub_bound_cannot_overflow(self, other):
        lower, no_ovf_lower = z3_sub_overflow(self.lower, other.upper)
        upper, no_ovf_upper = z3_sub_overflow(self.upper, other.lower)
        return z3.And(no_ovf_lower, no_ovf_upper)

    def and_bound(self, other):
        pos1 = self.known_nonnegative()
        pos2 = other.known_nonnegative()
        # the next three if-conditions are proven by test_prove_and_bound_logic
        lower = z3.If(z3.Or(pos1, pos2), z3.BitVecVal(0, LONG_BIT), MININT)
        upper = z3.If(
            pos1,
            z3.If(
                pos2,
                z3_min(self.upper, other.upper),
                self.upper),
            z3.If(
                pos2,
                other.upper,
                MAXINT))
        res_tvalue, res_tmask = self._tnum_and(other)
        return self.new(lower, upper, res_tvalue, res_tmask)

    def lshift_bound_cannot_overflow(self, other):
        _, no_ovf1 = z3_lshift_overflow(self.lower, other.lower)
        _, no_ovf2 = z3_lshift_overflow(self.lower, other.upper)
        _, no_ovf3 = z3_lshift_overflow(self.upper, other.lower)
        _, no_ovf4 = z3_lshift_overflow(self.upper, other.upper)
        return z3.And(no_ovf1, no_ovf2, no_ovf3, no_ovf4)

    def rshift_bound(self, other):
        result = self.concrete_variable >> other.concrete_variable
        result1 = self.lower >> other.lower
        result2 = self.lower >> other.upper
        result3 = self.upper >> other.lower
        result4 = self.upper >> other.upper
        min1 = z3_min(result1, result2, result3, result4)
        max1 = z3_max(result1, result2, result3, result4)
        cond = z3.And(other.lower >= 0, other.upper < LONG_BIT)
        min1 = z3.If(cond, min1, MININT)
        max1 = z3.If(cond, max1, MAXINT)
        tvalue, tmask = self._tnum_rshift(other.lower)
        cond2 = z3.And(other.is_constant(), cond)
        tvalue = z3.If(cond2,
                       tvalue, 0)
        tmask = z3.If(cond2,
                      tmask, -1)
        return Z3IntBound(min1, max1, tvalue, tmask)

    def urshift_bound(self, other):
        tvalue_if_const, tmask_if_const = self._tnum_urshift(other.lower)
        tvalue = z3.If(other.is_constant(), tvalue_if_const, 0)
        tmask = z3.If(other.is_constant(), tmask_if_const, -1)
        return Z3IntBound.from_knownbits(tvalue, tmask)

    def is_constant(self):
        return z3.And(self.lower == self.upper, self.tmask == 0)

    def is_bool(self):
        return z3.And(0 <= self.lower, self.upper <= 1)

    def known_eq_const(self, value):
        return z3.If(self.is_constant(), self.lower == value, False)

    def get_constant_int(self):
        return z3.If(self.is_constant(), self.lower, 0xdeadbeef)
    # ____________________________________________________________

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

def test_prove_and_bound_logic():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    res = b1.concrete_variable & b2.concrete_variable
    b3 = b1.and_bound(b2)
    b3.concrete_variable = res
    b1.prove_implies(
        b2,
        b3
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
    b3 = b1.add_bound(b2)
    b3.concrete_variable = result
    b1.prove_implies(
        b2,
        b3
    )

def test_prove_add_bound_cannot_overflow_logic():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    result, no_ovf_result = z3_add_overflow(b1.concrete_variable, b2.concrete_variable)
    b1.prove_implies(
        b2,
        b1.add_bound_cannot_overflow(b2),
        no_ovf_result,
    )

def test_prove_add_bound_no_overflow():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    result, no_ovf = z3_add_overflow(b1.concrete_variable, b2.concrete_variable)
    b3 = b1.add_bound_no_overflow(b2)
    b3.concrete_variable = result
    b1.prove_implies(
        b2,
        no_ovf,
        b3
    )

def test_prove_neg_logic():
    b1 = make_z3_intbounds_instance('self')
    one = Z3IntBound(BitVecVal(1), BitVecVal(1), BitVecVal(1), BitVecVal(0))
    b2 = b1.neg_bound()
    b2.concrete_variable = -b1.concrete_variable
    b1.prove_implies(b2)

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
    b3 = b1.sub_bound(b2)
    b3.concrete_variable = b1.concrete_variable - b2.concrete_variable
    b1.prove_implies(
        b2,
        b3
    )

def test_prove_sub_bound_cannot_overflow_logic():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    result, no_ovf_result = z3_sub_overflow(b1.concrete_variable, b2.concrete_variable)
    b1.prove_implies(
        b2,
        b1.sub_bound_cannot_overflow(b2),
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


def test_prove_known_eq_const_logic():
    b1 = make_z3_intbounds_instance('self')
    x = BitVec('x')
    b1.prove_implies(
        b1.known_eq_const(x),
        b1.concrete_variable == x
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
    res = b1.lshift_bound_cannot_overflow(b2)
    result, no_ovf = z3_lshift_overflow(b1.concrete_variable, b2.concrete_variable)
    b1.prove_implies(
        b2,
        res,
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

@z3_with_reduced_bitwidth(32)
def test_2_prove_rshift_bound_logic():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    b3 = b1.rshift_bound(b2)
    b3.concrete_variable = result = b1.concrete_variable >> b2.concrete_variable
    b1.prove_implies(
        b2,
        b2.lower >= 0,
        b2.upper < LONG_BIT,
        b3,
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

def test_prove_urshift_knownbits_logic():
    b1 = make_z3_intbounds_instance('self')
    b2 = make_z3_intbounds_instance('other')
    result = z3.LShR(b1.concrete_variable, b2.concrete_variable)
    b3 = b1.urshift_bound(b2)
    b3.concrete_variable = result
    b1.prove_implies(
        b2,
        b3,
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

""" The purpose of this test file is to do bounded model checking of the
IntBound methods with Z3.

The approach is to generate random bounds, then perform operations on them, and
ask Z3 whether the resulting bound is a sound approximation of the result.
"""

import pytest

from rpython.rlib.rarithmetic import LONG_BIT, r_uint, intmask
from rpython.jit.metainterp.optimizeopt.intutils import IntBound

try:
    import z3
    from hypothesis import given, strategies
except ImportError:
    pytest.skip("please install z3 (z3-solver on pypi) and hypothesis")

uints = strategies.builds(
    r_uint,
    strategies.integers(min_value=0, max_value=2**LONG_BIT - 1)
)

def build_some_bits_known(a, b):
    return IntBound(tvalue=a & ~b, tmask=b)

some_bits_known = strategies.builds(
    build_some_bits_known,
    uints, uints
)

varname_counter = 0

def to_z3(bound, variable=None):
    global varname_counter
    if variable is None:
        variable = z3.BitVec("bv%s" % (varname_counter, ), LONG_BIT)
        varname_counter += 1
    return variable, z3.And(variable <= z3.BitVecVal(bound.upper, LONG_BIT),
               variable >= z3.BitVecVal(bound.lower, LONG_BIT),
               variable & z3.BitVecVal(~bound.tmask, LONG_BIT) == z3.BitVecVal(bound.tvalue, LONG_BIT))


solver = z3.Solver()

def prove(cond):
    z3res = solver.check(z3.Not(cond))
    if z3res == z3.unsat:
        pass
    elif z3res == z3.unknown:
        pass
    elif z3res == z3.sat:
        # not possible to prove!
        # print some nice stuff
        model = solver.model()
        import pdb;pdb.set_trace()

@given(some_bits_known, some_bits_known)
def test_add(b1, b2):
    print "_" * 60
    b3 = b1.add_bound(b2)
    var1, formula1 = to_z3(b1)
    var2, formula2 = to_z3(b2)
    var3, formula3 = to_z3(b3, var1 + var2)
    print b1
    print b2
    print b3
    print formula1
    print formula2
    print formula3
    cond = z3.Implies(z3.And(formula1, formula2), formula3)
    print cond
    prove(cond)

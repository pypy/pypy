# the place to put z3 tests for rlib functionality

import pytest
import sys
import gc

try:
    import z3
    from hypothesis import given, strategies, assume, example
except ImportError:
    pytest.skip("please install z3 (z3-solver on pypi) and hypothesis")


from rpython.rlib.rbigint import _bitcount64_ops

def test_bitcount64_logic():

    BITCOUNT_K1 = z3.BitVecVal(0x5555555555555555, 64) # Repeating 01
    BITCOUNT_K2 = z3.BitVecVal(0x3333333333333333, 64) # Repeating 0011
    BITCOUNT_K4 = z3.BitVecVal(0x0f0f0f0f0f0f0f0f, 64) # Repeating 00001111
    BITCOUNT_KF = z3.BitVecVal(0x0101010101010101, 64) # Repeating 00000001

    x = z3.BitVec('x', 64)

    solver = z3.Solver()
    solver.add(x >= 0)
    solver.add(x <= 100000000)

    res = _bitcount64_ops(x, BITCOUNT_K1, BITCOUNT_K2, BITCOUNT_K4, BITCOUNT_KF)
    zero = z3.BitVecVal(0, 64)
    one = z3.BitVecVal(1, 64)
    correct_res = zero
    for i in range(64):
        correct_res += z3.If(z3.Extract(i, i, x) == 1, one, zero)
    status = solver.check(res != correct_res)
    assert status == z3.unsat


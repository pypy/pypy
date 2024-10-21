import pytest
try:
    import rply
    import z3
except ImportError:
    pytest.skip('rply or z3 not installed')

from rpython.rlib.rarithmetic import LONG_BIT, r_uint, intmask, ovfcheck, uint_mul_high

from rpython.jit.metainterp.ruleopt.proof import *

import os
with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "real.rules")) as f:
    ALLRULES = f.read()




def test_higest_bit():
    for i in range(64):
        assert highest_bit(r_uint(1) << i) == i


@pytest.mark.parametrize("name,rule", [(rule.name, rule) for rule in parse.parse(ALLRULES).rules if not rule.cantproof])
def test_z3_prove(name, rule):
    p = Prover()
    try:
        p.check_rule(rule)
    except ProofProblem as e:
        print e.format()
        raise

def test_sorry():
    s = """\
eq_different_knownbits: int_eq(x, y)
    SORRY_Z3
    => 0
    """
    prove_source(s)

def test_explain_problem():
    s = """\
bug: int_and(x, y)
    => 1
    """
    with pytest.raises(CouldNotProve) as info:
        prove_source(s)
    assert info.value.format() == '''\
Could not prove correctness of rule 'bug'
in line 1
counterexample given by Z3:
counterexample values:
x: 0
y: 0
operation int_and(x, y) with Z3 formula x & y
has counterexample result vale: 0
BUT
target expression: 1 with Z3 formula 1
has counterexample value: 1'''

def test_explain_problem_empty():
    s = """\
never_applies: int_is_true(x)
    check x.known_lt_const(0) and x.known_gt_const(0) # impossible condition
    => x
"""
    with pytest.raises(RuleCannotApply) as info:
        prove_source(s)
    assert info.value.format() == '''\
Rule 'never_applies' cannot ever apply
in line 1
Z3 did not manage to find values for variables x such that the following condition becomes True:
And(x <= x_upper,
    x_lower <= x,
    If(x_upper < 0, x_lower > 0, x_upper < 0))\
'''

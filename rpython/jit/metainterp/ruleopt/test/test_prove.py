import pytest
try:
    import rply
    import z3
except ImportError:
    pytest.skip('rply or z3 not installed')

from rpython.rlib.rarithmetic import LONG_BIT, r_uint, intmask, ovfcheck, uint_mul_high

from rpython.jit.metainterp.ruleopt.proof import *

import os
with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "all.rules")) as f:
    ALLRULES = f.read()




def test_higest_bit():
    for i in range(64):
        assert highest_bit(r_uint(1) << i) == i


@pytest.mark.parametrize("name,rule", [(rule.name, rule) for rule in parse.parse(ALLRULES).rules])
def test_z3_prove(name, rule):
    p = Prover()
    p.check_rule(rule)

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

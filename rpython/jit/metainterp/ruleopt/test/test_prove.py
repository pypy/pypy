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


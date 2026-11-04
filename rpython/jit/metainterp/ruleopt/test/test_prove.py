import pytest
try:
    import rply
    import z3
except ImportError:
    pytest.skip('rply or z3 not installed', allow_module_level=True)

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

@pytest.mark.parametrize('suffix', ['lt', 'le', 'gt', 'ge'])
def test_known_unsigned_comparison(suffix):
    prove_source('''\
unsigned_comparison: uint_%s(x, y)
    check x.known_unsigned_%s(y)
    => 1
''' % (suffix, suffix), force=True)


def test_sorry():
    s = """\
eq_different_knownbits: int_eq(x, y)
    SORRY_Z3
    => 0
    """
    prove_source(s)


def test_known_ne_contract_does_not_execute_method(monkeypatch):
    def unsupported(*args):
        raise AssertionError('must use the contract, not the implementation')
    monkeypatch.setattr(IntBound, 'known_ne', unsupported)
    prove_source('''\
ne_contract: int_ne(x, y)
    check x.known_ne(y)
    => 1
''', force=True)


@pytest.mark.parametrize('check', [
    'x.known_ne(y)',
    'x.known_ne(y) or x.lower == x.lower',
])
def test_known_ne_contract_rejects_incorrect_rule(check):
    # The first rule reverses the result; the second can bypass the check.
    target = '1' if check == 'x.known_ne(y)' else '0'
    source = '''\
wrong: int_eq(x, y)
    check %s
    => %s
''' % (check, target)
    with pytest.raises(CouldNotProve):
        prove_source(source, force=True)


def test_known_ne_contract_cannot_apply_to_self():
    with pytest.raises(RuleCannotApply):
        prove_source('''\
impossible: int_eq(x, x)
    check x.known_ne(x)
    => 0
''', force=True)


@pytest.mark.parametrize('equal,result,expected', [
    (False, True, z3.sat),
    (False, False, z3.sat),
    (True, True, z3.unsat),
    (True, False, z3.sat),
])
def test_known_ne_contract_concrete_operands(equal, result, expected):
    prover = Prover()
    left = make_z3_intbounds_instance('left')
    right = make_z3_intbounds_instance('right')
    opaque = prover.call_method_with_contract('known_ne', left, right)
    solver = z3.Solver()
    solver.add(*prover.glue_conditions)
    solver.add(opaque == result)
    # Overlapping bounds deliberately remain possible when the concrete
    # operands differ: we instantiate soundness only for these operands.
    solver.add(left.lower == 0, left.upper == 2,
               right.lower == 1, right.upper == 4,
               left.tvalue == 0, left.tmask == -1,
               right.tvalue == 0, right.tmask == -1,
               left.concrete_variable == 1,
               right.concrete_variable == (1 if equal else 4),
               left.z3_formula(), right.z3_formula())
    assert solver.check() == expected


def test_known_ne_contract_disjoint_knownbits():
    prover = Prover()
    left = make_z3_intbounds_instance('left')
    right = make_z3_intbounds_instance('right')
    result = prover.call_method_with_contract('known_ne', left, right)
    solver = z3.Solver()
    solver.add(*prover.glue_conditions)
    # Same ranges, but one contains only even values and the other only odd.
    solver.add(result, left.lower == 0, left.upper == 3,
               right.lower == 0, right.upper == 3,
               left.tmask == -2, left.tvalue == 0,
               right.tmask == -2, right.tvalue == 1,
               left.z3_formula(), right.z3_formula())
    assert solver.check() == z3.sat


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

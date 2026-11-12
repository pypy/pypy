from __future__ import print_function

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




def test_highest_bit():
    from rpython.rlib.rarithmetic import highest_bit as runtime_highest_bit
    values = [0, 14, -1, -14]
    for i in range(LONG_BIT):
        power = r_uint(1) << i
        assert highest_bit(power) == i
        values.extend([power, power - 1, power | 1, intmask(power)])
    for value in values:
        expected = runtime_highest_bit(value)
        assert intmask(highest_bit(r_uint(value))) == expected
        result = z3.simplify(z3_highest_bit(z3.BitVecVal(value, LONG_BIT)))
        assert intmask(result.as_long()) == expected


@pytest.mark.parametrize('value,expected', [
    (0, -1),
    (-1, LONG_BIT - 1),
    (-2, LONG_BIT - 1),
    (-14, LONG_BIT - 1),
    (-(1 << (LONG_BIT - 1)), LONG_BIT - 1),
])
def test_highest_bit_zero_and_negative(value, expected):
    from rpython.rlib.rarithmetic import highest_bit as runtime_highest_bit
    assert runtime_highest_bit(value) == expected
    assert intmask(highest_bit(r_uint(value))) == expected
    result = z3.simplify(z3_highest_bit(z3.BitVecVal(value, LONG_BIT)))
    assert intmask(result.as_long()) == expected


@pytest.mark.parametrize('value,expected', [(0, -1), (3, 1), (14, 3),
                                          (-1, LONG_BIT - 1)])
def test_highest_bit_rule(value, expected):
    prove_source('''\
highest_bit_result: int_add(x, C)
    check C == %s
    H = highest_bit(C)
    D = H + %s
    => int_add(x, D)
''' % (value, value - expected), force=True)


@pytest.mark.parametrize("name,rule", [(rule.name, rule) for rule in parse.parse(ALLRULES).rules if not rule.cantproof])
def test_z3_prove(name, rule):
    p = Prover()
    try:
        p.check_rule(rule)
    except ProofProblem as e:
        print(e.format())
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


@pytest.mark.parametrize('body', [
    'check x.is_constant()\n    C = x.get_constant_int()',
    'check x.known_eq_const(0)\n    C = x.get_constant_int()',
    'check x.is_constant() and x.get_constant_int() == 0',
    'check 1 == 1 or x.get_constant_int() == 0',
    'bound = x.and_bound(x)\n    check bound.is_constant()\n    C = bound.get_constant_int()',
])
def test_get_constant_int_precondition(body):
    prove_source('''\
constant_precondition: int_add(x, 0)
    %s
    => x
''' % body, force=True)


@pytest.mark.parametrize('body', [
    'C = x.get_constant_int()',
    'C = x.get_constant_int()\n    check x.is_constant()',
    'check x.get_constant_int() == 0',
    'check x.get_constant_int() == 0 and x.is_constant()',
    'check x.is_constant() or x.get_constant_int() == 0',
    'bound = x.and_bound(x)\n    C = bound.get_constant_int()\n    check bound.is_constant()',
])
def test_get_constant_int_missing_precondition(body):
    with pytest.raises(CouldNotProvePrecondition) as exc:
        prove_source('''\
missing_precondition: int_add(x, 0)
    %s
    => x
''' % body, force=True)
    message = exc.value.format()
    assert "Could not prove precondition in rule 'missing_precondition'" in message
    assert 'in line ' in message


@pytest.mark.parametrize('body', [
    'H = highest_bit(C)',
    'check highest_bit(C) >= 0',
    'check 0 <= C and C < LONG_BIT\n    D = 1 << C',
    'check 0 <= C and C < LONG_BIT and (1 << C) > 0',
])
def test_expression_preconditions(body):
    prove_source('''\
expression_precondition: int_add(x, C)
    %s
    => int_add(x, C)
''' % body, force=True)


@pytest.mark.parametrize('body', [
    'D = 1 << C\n    check 0 <= C and C < LONG_BIT',
    'check (1 << C) == 1',
])
def test_expression_missing_preconditions(body):
    with pytest.raises(CouldNotProvePrecondition):
        prove_source('''\
missing_precondition: int_add(x, C)
    %s
    => int_add(x, C)
''' % body, force=True)


def test_precondition_invalidates_old_proof_cache(tmpdir, monkeypatch):
    from rpython.jit.metainterp.ruleopt import proof
    source = '''\
old_cached_rule: int_add(x, 0)
    C = x.get_constant_int()
    => x
'''
    old_hash = md5('\n'.join(source.splitlines())).hexdigest()
    tmpdir.join('jit_dsl_rule_' + old_hash).write(source)
    monkeypatch.setattr(proof, 'CACHE_DIR', str(tmpdir))
    with pytest.raises(CouldNotProvePrecondition):
        prove_source(source)


def test_and_bound_contract_rejects_unshrunk_lower():
    # The old model fixed this lower bound at zero. The runtime shrinks it:
    # for x == 3, this rule would incorrectly replace 1 with 4.
    with pytest.raises(CouldNotProve):
        prove_source('''\
wrong_and_lower: int_eq(x, x)
    check x.known_nonnegative()
    bound = x.and_bound(x)
    C = bound.lower
    D = C + 1
    => D
''', force=True)


def test_and_bound_contract_composes():
    prove_source('''\
and_urshift: uint_rshift(int_and(x, y), n)
    bound = x.and_bound(y)
    result = bound.urshift_bound(n)
    check result.is_constant()
    C = result.get_constant_int()
    => C
''', force=True)


BOUND_METHODS = [
    ('and_bound', 'int_and'), ('or_bound', 'int_or'),
    ('sub_bound', 'int_sub'), ('lshift_bound', 'int_lshift'),
    ('rshift_bound', 'int_rshift'), ('urshift_bound', 'uint_rshift'),
]


@pytest.mark.parametrize('method,op', BOUND_METHODS)
def test_bound_contract_does_not_execute_method(monkeypatch, method, op):
    def unsupported(*args):
        raise AssertionError('must use the contract, not the implementation')
    monkeypatch.setattr(IntBound, method, unsupported)
    prove_source('''\
bound_contract: %s(x, y)
    bound = x.%s(y)
    check bound.is_constant()
    C = bound.get_constant_int()
    => C
''' % (op, method), force=True)


@pytest.mark.parametrize('method,op', BOUND_METHODS)
def test_bound_contract_rejects_incorrect_rule(method, op):
    with pytest.raises(CouldNotProve):
        prove_source('''\
wrong_bound: %s(x, y)
    bound = x.%s(y)
    check bound.is_constant()
    C = bound.get_constant_int()
    D = C + 1
    => D
''' % (op, method), force=True)


@pytest.mark.parametrize('method,op', BOUND_METHODS)
def test_bound_contract_composes(method, op):
    prove_source('''\
bound_twice: %s(%s(x, y), y)
    bound = x.%s(y)
    result = bound.%s(y)
    check result.is_constant()
    C = result.get_constant_int()
    => C
''' % (op, op, method, method), force=True)


@pytest.mark.parametrize('lower,upper,tvalue,tmask,expected', [
    (5, 10, 0, -1, z3.sat), (0, 15, 0, -1, z3.sat),
    (8, 8, 8, 0, z3.sat), (0, 7, 0, -1, z3.unsat),
    (0, 15, 1, -2, z3.unsat),  # known odd: cannot contain 16 >>u 1
])
def test_urshift_bound_contract_concrete_operands(lower, upper, tvalue, tmask, expected):
    prover = Prover()
    left = make_z3_intbounds_instance('left')
    right = make_z3_intbounds_instance('right')
    result = prover.call_method_with_contract('urshift_bound', left, right)
    solver = z3.Solver()
    solver.add(*prover.glue_conditions)
    solver.add(left.concrete_variable == 16, right.concrete_variable == 1,
               result.lower == lower, result.upper == upper,
               result.tvalue == tvalue, result.tmask == tmask)
    assert solver.check() == expected


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

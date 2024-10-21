import sys
import os
from hashlib import md5

import z3

from rpython.jit.metainterp.optimizeopt.test.test_z3intbound import (
    make_z3_intbounds_instance,
)
from rpython.jit.metainterp.optimizeopt.intutils import IntBound
from rpython.jit.metainterp.ruleopt import parse
from rpython.rlib.rarithmetic import LONG_BIT, intmask, r_uint

from rpython.config.translationoption import CACHE_DIR
from rpython.tool.gcc_cache import try_atomic_write

MAXINT = sys.maxint
MININT = -sys.maxint - 1

class ProofProblem(Exception):
    pass

class CouldNotProve(ProofProblem):
    def __init__(self, rule, cond, model, lhs, rhs, prover):
        self.rule = rule
        self.cond = cond
        self.model = model
        self.rhs = rhs
        self.lhs = lhs
        self.prover = prover

    def format(self):
        rule = self.rule
        res = ["Could not prove correctness of rule '%s'" % self.rule.name]
        if self.rule.sourcepos:
            res.append("in line %s" % (self.rule.sourcepos.lineno, ))
        prover = self.prover
        model = prover.solver.model()
        detail = []
        res.append("counterexample given by Z3:")
        res.append("counterexample values:")
        for name, bound in prover.name_to_intbound.iteritems():
            if name in prover.glue_conditions_added:
                realbound = IntBound(model.evaluate(bound.lower).as_signed_long(),
                                      model.evaluate(bound.upper).as_signed_long(),
                                      r_uint(model.evaluate(bound.tmask).as_signed_long()),
                                      r_uint(model.evaluate(bound.tvalue).as_signed_long()),)
                details.append("bounds for %s: %s" % (name, bound))
            res.append("%s: %s" % (name, model[prover.name_to_z3[name]].as_signed_long()))
        res.append("operation %s with Z3 formula %s" % (rule.pattern, self.lhs))
        res.append("has counterexample result vale: %s" % (model.evaluate(self.lhs).as_signed_long(), ))
        res.append("BUT")
        res.append("target expression: %s with Z3 formula %s" % (rule.target, self.rhs))
        res.append("has counterexample value: %s" % (model.evaluate(self.rhs).as_signed_long(), ))
        res.extend(detail)
        return "\n".join(res)

class RuleCannotApply(ProofProblem):
    def __init__(self, rule, cond, prover):
        self.rule = rule
        self.cond = cond
        self.prover = prover

    def format(self):
        rule = self.rule
        res = ["Rule '%s' cannot ever apply" % self.rule.name]
        if self.rule.sourcepos:
            res.append("in line %s" % (self.rule.sourcepos.lineno, ))
        prover = self.prover
        res.append("Z3 did not manage to find values for variables %s such that the following condition becomes True:" % ", ".join(prover.name_to_z3))
        res.append(str(self.cond))
        return "\n".join(res)

TRUEBV = z3.BitVecVal(1, LONG_BIT)
FALSEBV = z3.BitVecVal(0, LONG_BIT)


def z3_cond(z3expr):
    return z3.If(z3expr, TRUEBV, FALSEBV)


def z3_bool_expression(opname, arg0, arg1=None):
    expr = None
    valid = True
    if opname == "int_eq":
        expr = arg0 == arg1
    elif opname == "int_ne":
        expr = arg0 != arg1
    elif opname == "int_lt":
        expr = arg0 < arg1
    elif opname == "int_le":
        expr = arg0 <= arg1
    elif opname == "int_gt":
        expr = arg0 > arg1
    elif opname == "int_ge":
        expr = arg0 >= arg1
    elif opname == "uint_lt":
        expr = z3.ULT(arg0, arg1)
    elif opname == "uint_le":
        expr = z3.ULE(arg0, arg1)
    elif opname == "uint_gt":
        expr = z3.UGT(arg0, arg1)
    elif opname == "uint_ge":
        expr = z3.UGE(arg0, arg1)
    elif opname == "int_is_true":
        expr = arg0 != FALSEBV
    elif opname == "int_is_zero":
        expr = arg0 == FALSEBV
    else:
        assert 0
    return expr, valid


def z3_expression(opname, arg0, arg1=None):
    expr = None
    valid = True
    if opname == "int_add":
        expr = arg0 + arg1
    elif opname == "int_sub":
        expr = arg0 - arg1
    elif opname == "int_mul":
        expr = arg0 * arg1
    elif opname == "int_and":
        expr = arg0 & arg1
    elif opname == "int_or":
        expr = arg0 | arg1
    elif opname == "int_xor":
        expr = arg0 ^ arg1
    elif opname == "int_lshift":
        expr = arg0 << arg1
        valid = z3.And(arg1 >= 0, arg1 < LONG_BIT)
    elif opname == "int_rshift":
        expr = arg0 >> arg1
        valid = z3.And(arg1 >= 0, arg1 < LONG_BIT)
    elif opname == "uint_rshift":
        expr = z3.LShR(arg0, arg1)
        valid = z3.And(arg1 >= 0, arg1 < LONG_BIT)
    elif opname == "uint_mul_high":
        # zero-extend args to 2*LONG_BIT bit, then multiply and extract
        # highest LONG_BIT bits
        zarg0 = z3.ZeroExt(LONG_BIT, arg0)
        zarg1 = z3.ZeroExt(LONG_BIT, arg1)
        expr = z3.Extract(LONG_BIT * 2 - 1, LONG_BIT, zarg0 * zarg1)
    elif opname == "int_neg":
        expr = -arg0
    elif opname == "int_invert":
        expr = ~arg0
    elif opname == "int_force_ge_zero":
        expr = z3.If(arg0 < 0, 0, arg0)
    else:
        expr, valid = z3_bool_expression(opname, arg0, arg1)
        return z3_cond(expr), valid
    return expr, valid


def z3_and(*args):
    args = [arg for arg in args if arg is not True]
    if args:
        if len(args) == 1:
            return args[0]
        return z3.And(*args)
    return True


def z3_implies(a, b):
    if a is True:
        return b
    return z3.Implies(a, b)


def popcount64(w):
    w -= (w >> 1) & 0x5555555555555555
    w = (w & 0x3333333333333333) + ((w >> 2) & 0x3333333333333333)
    w = (w + (w >> 4)) & 0x0F0F0F0F0F0F0F0F
    return ((w * 0x0101010101010101) >> 56) & 0xFF


def highest_bit(x):
    x |= x >> 1
    x |= x >> 2
    x |= x >> 4
    x |= x >> 8
    x |= x >> 16
    x |= x >> 32
    return popcount64(x) - 1


def z3_highest_bit(x):
    x |= z3.LShR(x, 1)
    x |= z3.LShR(x, 2)
    x |= z3.LShR(x, 4)
    x |= z3.LShR(x, 8)
    x |= z3.LShR(x, 16)
    x |= z3.LShR(x, 32)
    return popcount64(x) - 1


class Prover(parse.Visitor):
    def __init__(self):
        self.solver = z3.Optimize()
        self.name_to_z3 = {}
        self.name_to_intbound = {}
        self.glue_conditions_added = set()
        self.glue_conditions = []

    def prove(self, cond):
        z3res = self.solver.check(z3.Not(cond))
        if z3res == z3.unsat:
            return True
        elif z3res == z3.unknown:
            return False
        elif z3res == z3.sat:
            global model
            model = self.solver.model()
            return False

    def _convert_var(self, name):
        def newvar(name, suffix=""):
            if suffix:
                name += "_" + suffix
            res = z3.BitVec(name, LONG_BIT)
            self.name_to_z3[name] = res
            return res

        if name in self.name_to_z3:
            return self.name_to_z3[name]
        res = newvar(name)
        self.solver.minimize(res)
        b = make_z3_intbounds_instance(name, res)
        self.name_to_intbound[name] = b
        return res

    def _convert_intbound(self, name):
        b = self.name_to_intbound[name]
        if name not in self.glue_conditions_added:
            self.glue_conditions.append(b.z3_formula())
            self.glue_conditions_added.add(name)
        return b

    def _convert_attr(
        self,
        varname,
        attrname,
    ):
        b = self._convert_intbound(varname)
        return getattr(b, attrname)

    def visit_PatternOp(self, pattern):
        args = [self.visit(arg) for arg in pattern.args]
        res, valid = z3_expression(pattern.opname, *[arg[0] for arg in args])
        return res, z3_and(valid, *[arg[1] for arg in args])

    def visit_PatternVar(self, pattern):
        return self._convert_var(pattern.name), True

    def visit_PatternConst(self, pattern):
        if pattern.const == "LONG_BIT":
            return z3.BitVecVal(LONG_BIT, LONG_BIT)
        elif pattern.const == "MININT":
            return z3.BitVecVal(MININT, LONG_BIT), True
        elif pattern.const == "MAXINT":
            return z3.BitVecVal(MAXINT, LONG_BIT), True
        res = z3.BitVecVal(pattern.const, LONG_BIT)
        return res, True

    def visit_ShortcutOr(self, expr, targettype=int):
        assert targettype is bool
        left, leftvalid = self.visit(expr.left, bool)
        right, rightvalid = self.visit(expr.right, bool)
        res = z3.If(left, left, right)
        return res, z3_and(leftvalid, rightvalid)

    def visit_ShortcutAnd(self, expr, targettype=int):
        assert targettype is bool
        left, leftvalid = self.visit(expr.left, bool)
        right, rightvalid = self.visit(expr.right, bool)
        res = z3.If(left, right, left)
        return res, z3_and(leftvalid, rightvalid)

    def visit_BinOp(self, expr, targettype=int):
        left, leftvalid = self.visit(expr.left, int)
        right, rightvalid = self.visit(expr.right, int)
        if targettype is int:
            res, valid = z3_expression(expr.opname, left, right)
        else:
            assert targettype is bool
            res, valid = z3_bool_expression(expr.opname, left, right)
        return res, z3_and(leftvalid, rightvalid, valid)

    def visit_UnaryOp(self, expr, targettype=int):
        assert targettype is int
        left, leftvalid = self.visit(expr.left, targettype)
        res, valid = z3_expression(expr.opname, left)
        return res, z3_and(leftvalid, valid)

    def visit_Name(self, expr, targettype=int):
        if expr.name == "LONG_BIT":
            return 64, True
        if expr.name == "MAXINT":
            return MAXINT, True
        if expr.name == "MININT":
            import pdb;pdb.set_trace()
            return MININT, True
        if targettype is int:
            var = self._convert_var(expr.name)
            return var, True
        if targettype is IntBound:
            b = self._convert_intbound(expr.name)
            return b, True
        import pdb

        pdb.set_trace()

    def visit_Number(self, expr, targettype=int):
        assert targettype is int
        res = z3.BitVecVal(expr.value, LONG_BIT)
        return res, True

    def visit_Attribute(self, expr, targettype=int):
        res = self._convert_attr(expr.varname, expr.attrname)
        return res, True

    def visit_MethodCall(self, expr, targettype=int):
        res, resvalid = self.visit(expr.value, IntBound)
        assert isinstance(res, IntBound)
        args = [
            self.visit(arg, arg.typ) for arg in expr.args
        ]
        methargs = [arg[0] for arg in args]
        return getattr(res, expr.methname)(*methargs), z3_and(
            resvalid, *[arg[1] for arg in args]
        )

    def visit_FuncCall(self, expr, targettype=int):
        targettypes = [int] * len(expr.args)
        args = [
            self.visit(arg, typ) for arg, typ in zip(expr.args, targettypes)
        ]
        func = globals()["z3_" + expr.funcname]
        funcargs = [arg[0] for arg in args]
        return func(*funcargs), z3_and(*[arg[1] for arg in args])

    def must_be_sat(self, rule, lhs, *conditions):
        def _find_index_to_remove():
            for removeindex in range(len(conditions)):
                if self.solver.check(z3_and(lhs == somevar, *(conditions[:removeindex] + conditions[removeindex + 1:]))) == z3.unsat:
                    return removeindex
            return -1
        todo = list(conditions)
        conditions = []
        while todo:
            c = todo.pop()
            if c is True:
                continue
            if c.decl().name() == 'and':
                todo.extend(c.children())
            else:
                conditions.append(c)

        somevar = z3.BitVec('check_not_empty', LONG_BIT)
        conditions.append(lhs == somevar)
        cond = z3_and(*conditions)
        if self.solver.check(cond) != z3.sat:
            # try to remove conditions
            while 1:
                removeindex = _find_index_to_remove()
                if removeindex >= 0:
                    del conditions[removeindex]
                    cond = z3_and(*conditions)
                else:
                    break
            raise RuleCannotApply(rule, cond, self)

    def check_rule(self, rule):
        import time
        t1 = time.time()
        print("checking %s" % rule)
        lhs, lhsvalid = self.visit(rule.pattern)
        self.must_be_sat(rule, lhs, lhsvalid)
        rhs, rhsvalid = self.visit(rule.target)
        implies_left = [lhsvalid]
        implies_right = [rhsvalid, rhs == lhs]
        for el in rule.elements:
            if isinstance(el, parse.Compute):
                expr, exprvalid = self.visit(el.expr, int)
                if el.expr.typ is not IntBound:
                    implies_left.append(self._convert_var(el.name) == expr)
                    implies_right.append(exprvalid)
                else:
                    self.name_to_intbound[el.name] = expr
                    self.glue_conditions_added.add(el.name)
                continue
            if isinstance(el, parse.Check):
                expr, _ = self.visit(el.expr, bool)
                implies_left.append(expr)
                continue
            assert 0, "unreachable"
        implies_left.extend(self.glue_conditions)
        self.must_be_sat(rule, lhs, lhsvalid, *implies_left)
        condition = z3_implies(z3_and(*implies_left), z3_and(*implies_right))
        print(condition)
        if not self.prove(condition):
            raise CouldNotProve(rule, condition, model, lhs, rhs, self)
        t2 = time.time()
        print("took %s seconds" % (t2 - t1))


def prove_source(s, force=False):
    lines = s.splitlines()
    ast = parse.parse(s)
    for rule in ast.rules:
        if rule.cantproof:
            print "SKIPPING PROOF!", rule.name
            continue
        cachename = None
        if not force:
            start_lineno = rule.sourcepos.lineno - 1
            end_lineno = rule.endsourcepos.lineno
            rule_lines = lines[start_lineno:end_lineno]

            h = md5("\n".join(rule_lines))
            cachename = os.path.join(
                CACHE_DIR, "jit_dsl_rule_%s" % (h.hexdigest(), ))
            try:
                with open(cachename, 'rb') as f:
                    f.read() # just needs to exist, really
                print "reusing previous proof", rule.name
                continue
            except IOError:
                pass
        p = Prover()
        p.check_rule(rule)
        if cachename is not None:
            try_atomic_write(cachename, "\n".join(rule_lines))
    return ast

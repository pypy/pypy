import z3
from rpython.jit.metainterp.optimizeopt.test.test_z3intbound import (
    Z3IntBound,
    make_z3_intbounds_instance,
)
from rpython.jit.metainterp.ruleopt import parse
from rpython.rlib.rarithmetic import LONG_BIT


class CouldNotProve(Exception):
    pass


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
        self.solver = z3.Solver()
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
            return MININT, True
        var = self._convert_var(expr.name)
        if targettype is int:
            return var, True
        if targettype is Z3IntBound:
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
        res, resvalid = self.visit(expr.value, Z3IntBound)
        assert isinstance(res, Z3IntBound)
        if expr.methname in ("known_eq_const", "known_le_const", "known_ge_const"):
            targettypes = [int]
        else:
            targettypes = [Z3IntBound] * len(expr.args)
        args = [
            self.visit(arg, typ) for arg, typ in zip(expr.args, targettypes)
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

    def check_rule(self, rule):
        lhs, lhsvalid = self.visit(rule.pattern)
        rhs, rhsvalid = self.visit(rule.target)
        implies_left = [lhsvalid]
        implies_right = [rhsvalid, rhs == lhs]
        for el in rule.elements:
            if isinstance(el, parse.Compute):
                expr, exprvalid = self.visit(el.expr, int)
                implies_left.append(self._convert_var(el.name) == expr)
                implies_right.append(exprvalid)
                continue
            if isinstance(el, parse.Check):
                expr, _ = self.visit(el.expr, bool)
                implies_left.append(expr)
                continue
            assert 0, "unreachable"
        implies_left.extend(self.glue_conditions)
        condition = z3_implies(z3_and(*implies_left), z3_and(*implies_right))
        print("checking %s" % rule)
        print(condition)
        assert self.prove(condition)


def prove_source(s):
    ast = parse.parse(s)
    for rule in ast.rules:
        if rule.cantproof:
            print "SKIPPING PROOF!", rule.name
            continue
        p = Prover()
        p.check_rule(rule)
    return ast

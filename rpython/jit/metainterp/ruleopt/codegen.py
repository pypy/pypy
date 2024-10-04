from contextlib import contextmanager
from collections import defaultdict

from rpython.jit.metainterp.ruleopt import parse
from rpython.jit.metainterp.optimizeopt.intutils import IntBound

commutative_ops = {"int_add", "int_mul", "int_eq", "int_ne"}


def generate_commutative_patterns_args(args):
    if not args:
        yield []
        return
    arg0 = args[0]
    args1 = args[1:]
    for subarg0 in generate_commutative_patterns(arg0):
        for subargs1 in generate_commutative_patterns_args(args1):
            yield [subarg0] + subargs1


def generate_commutative_patterns(pattern):
    if not isinstance(pattern, parse.PatternOp):
        yield pattern
        return
    for subargs in generate_commutative_patterns_args(pattern.args):
        if pattern.opname not in commutative_ops:
            yield pattern.newargs(subargs)
        else:
            yield pattern.newargs(subargs)
            yield pattern.newargs(subargs[::-1])


def generate_commutative_rules(rule):
    for pattern in generate_commutative_patterns(rule.pattern):
        yield rule.newpattern(pattern)

def sort_rules(rules):
    return sorted(
        rules, key=lambda rule: (rule.target.sort_key_result(), rule.pattern.sort_key())
    )



class Codegen(parse.Visitor):
    def __init__(self):
        self.code = []
        self.level = 0

    @contextmanager
    def emit_indent(self, line=None):
        if line is not None:
            self.emit(line)
        self.level += 1
        yield
        self.level -= 1

    def emit_stacking_condition(self, cond):
        self.emit("if %s:" % cond)
        self.level += 1

    def emit(self, line=""):
        if self.level == 0 and line.startswith(("def ", "class ")):
            self.code.append("")
        if not line.strip():
            self.code.append("")
        else:
            self.code.append("    " * self.level + line)

    def visit_PatternVar(self, p, varname, intbound_name):
        if p.name.startswith("C"):
            cname = "C_" + varname
            if p.name not in self.bindings:
                self.emit_stacking_condition("%s.is_constant()" % intbound_name)
                self.emit("%s = %s.get_constant_int()" % (cname, intbound_name))
                self.bindings[p.name] = cname
                return
            elif cname == self.bindings[p.name]:
                return
            return self.emit_stacking_condition(
                "%s.known_eq_const(%s)" % (intbound_name, self.bindings[p.name])
            )
        else:
            if p.name not in self.bindings:
                self.bindings[p.name] = varname
                self.intbound_bindings[p.name] = intbound_name
                return
            elif varname == self.bindings[p.name]:
                return
            return self.emit_stacking_condition(
                "%s is %s" % (varname, self.bindings[p.name])
            )

    def visit_PatternConst(self, p, varname, intbound_name):
        return self.emit_stacking_condition(
            "%s.known_eq_const(%s)" % (intbound_name, p.const)
        )

    def visit_PatternOp(self, p, varname, intbound_name):
        boxname = "%s_%s" % (varname, p.opname)
        self.emit(
            "%s = self.optimizer.as_operation(%s, rop.%s)"
            % (boxname, varname, p.opname.upper())
        )
        self.emit_stacking_condition("%s is not None" % boxname)
        boxnames, boundnames = self._emit_arg_reads(boxname, varname, len(p.args))
        self._pattern_arg_check(boxnames, boundnames, p.args)
        return

    def generate_target(self, target):
        if isinstance(target, parse.PatternVar):
            self.emit("self.make_equal_to(op, %s)" % self.bindings[target.name])
            return
        if isinstance(target, parse.PatternConst):
            self.emit("self.make_constant_int(op, %s)" % target.const)
            return
        if isinstance(target, parse.PatternOp):
            args = []
            for arg in target.args:
                if isinstance(arg, parse.PatternVar):
                    if arg.name.startswith('C'):
                        args.append("ConstInt(%s)" % self.bindings[arg.name])
                    else:
                        args.append(self.bindings[arg.name])
                elif isinstance(arg, PatternConst):
                    args.append("ConstInt(%s)" % arg.const)
                else:
                    assert 0
            self.emit(
                "newop = self.replace_op_with(op, rop.%s, args=[%s])"
                % (target.opname.upper(), ", ".join(args))
            )
            self.emit("self.optimizer.send_extra_operation(newop)")
            return
        assert 0

    def _pattern_arg_check(self, boxnames, boundnames, args):
        for i, p in enumerate(args):
            self.visit(p, boxnames[i], boundnames[i])

    def _emit_arg_reads(self, prefix, opname, numargs):
        boxnames = []
        boundnames = []
        for i in range(numargs):
            boxname = "%s_%s" % (prefix, i)
            boundname = "b_" + boxname
            boxnames.append(boxname)
            boundnames.append(boundname)
            self.emit("%s = get_box_replacement(%s.getarg(%s))" % (boxname, opname, i))
            self.emit("%s = self.getintbound(%s)" % (boundname, boxname))
        return boxnames, boundnames

    def generate_method(self, opname, rules):
        all_rules = []
        for rule in rules:
            all_rules.extend(generate_commutative_rules(rule))
        all_rules = sort_rules(all_rules)
        name_positions = {}
        names = []
        for rule in all_rules:
            if rule.name not in name_positions:
                name_positions[rule.name] = len(name_positions)
                names.append(rule.name)
        self.emit("_rule_names_%s = %r" % (opname, names))
        self.emit("_rule_fired_%s = [0] * %s" % (opname, len(names)))
        self.emit("_all_rules_fired.append((_rule_names_%s, _rule_fired_%s))" % (opname, opname))
        with self.emit_indent("def optimize_%s(self, op):" % opname.upper()):
            numargs = len(rules[0].pattern.args)
            boxnames, boundnames = self._emit_arg_reads("arg", "op", numargs)
            for ruleindex, rule in enumerate(all_rules):
                self.bindings = {}
                self.intbound_bindings = {}
                self.emit("# %s: %s => %s" % (rule.name, rule.pattern, rule.target))
                currlevel = self.level
                checks = []
                self._pattern_arg_check(boxnames, boundnames, rule.pattern.args)
                for el in rule.elements:
                    self.visit(el)
                self.generate_target(rule.target)
                self.emit("self._rule_fired_%s[%s] += 1" % (opname, name_positions[rule.name]))
                self.emit("return")
                self.level = currlevel
            self.emit("return self.emit(op)")

    def visit_Compute(self, el):
        self.bindings[el.name] = el.name
        res = self.visit(el.expr)
        self.emit("%s = %s" % (el.name, res))

    def visit_Check(self, el):
        res = self.visit(el.expr)
        self.emit_stacking_condition(res)

    def visit_BinOp(self, expr, prec=0):
        left_prec = expr.precedence
        right_prec = expr.precedence + 1 # all left assoc for now
        left = self.visit(expr.left, left_prec)
        right = self.visit(expr.right, right_prec)
        res = "%s %s %s" % (left, expr.pysymbol, right)
        if prec > expr.precedence:
            res = "(" + res + ")"
        return res

    def visit_IntBinOp(self, expr, prec=0):
        if expr.need_ruint:
            left = self.visit(expr.left)
            right = self.visit(expr.right)
            return "intmask(r_uint(%s) %s r_uint(%s))" % (left, expr.pysymbol, right)

        return self.visit_BinOp(expr, prec)

    def visit_Name(self, expr, prec=0):
        if expr.name in ("LONG_BIT", ):
            return expr.name
        if expr.typ is IntBound:
            return self.intbound_bindings[expr.name]
        return self.bindings[expr.name]

    def visit_Attribute(self, expr, prec=0):
        return "%s.%s" % (expr.varname, expr.attrname)

    def visit_Number(self, expr, prec=0):
        return str(expr.value)

    def visit_UnaryOp(self, expr, prec=0):
        sub_prec = expr.precedence
        sub = self.visit(expr.left, sub_prec + 1)
        res = "%s%s" % (expr.pysymbol, sub)
        if prec > expr.precedence:
            res = "(" + res + ")"
        return res

    def visit_MethodCall(self, expr, prec=0):
        sub_prec = expr.precedence
        receiver = self.visit(expr.value)
        args = [self.visit(arg) for arg in expr.args]
        return "%s.%s(%s)" % (receiver, expr.methname, ", ".join(args))

    def visit_FuncCall(self, expr, prec=0):
        args = [self.visit(arg) for arg in expr.args]
        return "%s(%s)" % (expr.funcname, ", ".join(args))

    def generate_code(self, ast):
        per_op = defaultdict(list)
        for rule in ast.rules:
            per_op[rule.pattern.opname].append(rule)
        for opname, rules in per_op.items():
            self.generate_method(opname, rules)
        self.emit()
        return "\n".join(self.code)

    def generate_mixin(self, ast):
        with self.emit_indent("class OptIntAutoGenerated(object):"):
            self.emit("_all_rules_fired = []")
            return self.generate_code(ast)

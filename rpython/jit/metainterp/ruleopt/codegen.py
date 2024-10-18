from contextlib import contextmanager
from collections import defaultdict

from rpython.jit.metainterp.ruleopt import parse
from rpython.jit.metainterp.optimizeopt.intutils import IntBound

commutative_ops = {"int_add", "int_mul", "int_and", "int_mul", "int_or",
                   "int_xor", "int_eq", "int_ne"}


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
        if pattern.opname not in commutative_ops or str(subargs[0]) == str(subargs[1]):
            yield pattern.newargs(subargs)
        else:
            yield pattern.newargs(subargs)
            yield pattern.newargs(subargs[::-1])


def generate_commutative_rules(rule):
    for pattern in generate_commutative_patterns(rule.pattern):
        yield rule.newpattern(pattern)

def sort_rules(rules):
    return sorted(
        rules, key=lambda rule: rule.pattern.sort_key()
    )

def split_by_result_type(rules):
    constant_results = []
    box_results = []
    op_results = []
    for rule in rules:
        target = rule.target
        if isinstance(target, parse.PatternConst):
            constant_results.append(rule)
        elif isinstance(target, parse.PatternVar):
            if target.name.startswith('C'):
                constant_results.append(rule)
            else:
                box_results.append(rule)
        else:
            op_results.append(rule)
    return constant_results, box_results, op_results


class BaseMatcher(parse.BaseAst):
    pass


class Matcher(BaseMatcher):
    ifyes = None
    ifno = None
    nextmatcher = None


class IsConstMatcher(Matcher):
    def __init__(self, name, ifyes, ifno, nextmatcher, constname):
        self.name = name
        self.ifyes = ifyes
        self.ifno = ifno
        self.nextmatcher = nextmatcher
        self.constname = constname

class OpMatcher(Matcher):
    def __init__(self, name, opname, ifyes, ifno, nextmatcher, argnames):
        self.name = name
        self.opname = opname
        self.ifyes = ifyes
        self.ifno = ifno
        self.nextmatcher = nextmatcher
        self.argnames = argnames


class Terminal(BaseMatcher):
    def __init__(self, rules, bindings):
        self.rules = rules
        self.bindings = bindings

    def _dot(self, dotgen):
        label = [type(self).__name__ + " " + str(self.bindings)]
        for rule in self.rules:
            label.append(str(rule))
        dotgen.emit_node(str(id(self)), shape="box", label="\n".join(label))


def create_matcher(rules):
    assert len({rule.pattern.opname for rule in rules}) == 1
    # patterns is a list of lists, all the same length
    # len(patterns) == len(rules)
    patterns = [rule.pattern.args[:] for rule in rules]
    # names is a list of strings, as long as patterns[0]
    names = ["arg_%s" % i for i in range(len(patterns[0]))]
    name_paths = [((rules[0].pattern.opname, i), ) for i in range(len(patterns[0]))]
    bindings = {p: n for p, n in zip(name_paths, names)}
    res = _create_matcher(rules, patterns, names, name_paths, bindings)
    return res

def _create_matcher(rules, patterns, names, name_paths, bindings):
    if not rules:
        return None
    while patterns:
        assert len(names) == len(name_paths) == len(patterns[0])
        if len(patterns[0]) == 0:
            return Terminal(rules, bindings)
        matchpatterns = []
        matchrules = []
        cantmatchpatterns = []
        cantmatchrules = []
        restpatterns = []
        restrules = []
        newpatterns = []
        newnames = []
        if any(pattern[0].matches_constant() for pattern in patterns):
            name = names[0]
            for rule, pattern in zip(rules, patterns):
                if pattern[0].matches_constant():
                    matchrules.append(rule)
                    matchpatterns.append(pattern[1:])
                elif isinstance(pattern[0], parse.PatternOp):
                    cantmatchrules.append(rule)
                    cantmatchpatterns.append(pattern[:])
                else:
                    restrules.append(rule)
                    restpatterns.append(pattern[:])
            res = IsConstMatcher(names[0], None, None, None, "C_" + names[0])
            yes_name_paths = name_paths[1:]
            yes_bindings = bindings.copy()
            yes_bindings[name_paths[0] + ('C', )] = "C_" + names[0]
            ifyes = _create_matcher(matchrules, matchpatterns, names[1:], yes_name_paths, yes_bindings)
            ifno = _create_matcher(cantmatchrules, cantmatchpatterns, names[:], name_paths[:], bindings)
            nextmatcher = _create_matcher(restrules, restpatterns, names[:], name_paths, bindings)
            res.ifyes = ifyes
            res.ifno = ifno
            res.nextmatcher = nextmatcher
            return res
        elif any(isinstance(pattern[0], parse.PatternOp) for pattern in patterns):
            name = names[0]
            opname = None
            for rule, pattern in zip(rules, patterns):
                if isinstance(pattern[0], parse.PatternOp):
                    can_match = opname is None or (pattern[0].opname == opname)
                    if can_match:
                        opname = pattern[0].opname
                        matchrules.append(rule)
                        argnames = [names[0] + "_%s" % (i, ) for i in range(len(pattern[0].args))]
                        arg_paths = [name_paths[0] + ((opname, i), ) for i in range(len(pattern[0].args))]
                        matchpatterns.append(pattern[0].args + pattern[1:])
                    else:
                        cantmatchrules.append(rule)
                        cantmatchpatterns.append(pattern[:])
                    continue
                if pattern[0].matches_constant():
                    cantmatchrules.append(rule)
                    cantmatchpatterns.append(pattern[:])
                else:
                    restrules.append(rule)
                    restpatterns.append(pattern[:])
            res = OpMatcher(names[0], opname, None, None, None, argnames)
            yes_name_paths = arg_paths + name_paths[1:]
            yes_bindings = bindings.copy()
            for p, n in zip(arg_paths, argnames):
                yes_bindings[p] = n
            ifyes = _create_matcher(matchrules, matchpatterns, argnames + names[1:], yes_name_paths, yes_bindings)
            ifno = _create_matcher(cantmatchrules, cantmatchpatterns, names[:], name_paths[:], bindings)
            nextmatcher = _create_matcher(restrules, restpatterns, names[:], name_paths[:], bindings)
            res.ifyes = ifyes
            res.ifno = ifno
            res.nextmatcher = nextmatcher
            return res
        else:
            for pattern in patterns:
                del pattern[0]
            del names[0]
            del name_paths[0]
            continue
    return Terminal(rules, bindings)

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

    def default_visit(self, ast, *args, **kwargs):
        import pdb;pdb.set_trace()
        assert 0

    def visit_PatternVar(self, p):
        varname = self.bindings[p]
        if p.name.startswith("C"):
            assert varname.startswith("C_")
            if p.name not in self.bindings:
                self.bindings[p.name] = varname
                return
            if varname == self.bindings[p.name]:
                return
            return self.emit_stacking_condition(
                "%s == %s" % (varname, self.bindings[p.name])
            )
        else:
            intbound_name = "b_" + varname
            if p.name not in self.bindings:
                self.bindings[p.name] = varname
                self.intbound_bindings[p.name] = intbound_name
                return
            if varname == self.bindings[p.name]:
                return
            varname2 = self.bindings[p.name]
            return self.emit_stacking_condition(
                "self._eq(%s, b_%s, %s, b_%s)" % (varname, varname, varname2, varname2)
            )

    def visit_PatternConst(self, p):
        return self.emit_stacking_condition(
            "%s == %s" % (self.bindings[p], p.const)
        )

    def visit_PatternOp(self, p):
        for arg in p.args:
            self.visit(arg)
        return

    def generate_target(self, target):
        if isinstance(target, parse.PatternVar):
            if target.typ is int:
                value = "ConstInt(%s)" % self.bindings[target.name]
            else:
                value = self.bindings[target.name]
            self.emit("self.make_equal_to(op, %s)" % value)
            return
        if isinstance(target, parse.PatternConst):
            self.emit("self.make_constant_int(op, %s)" % target.const)
            return
        if isinstance(target, parse.PatternOp):
            args = []
            for arg in target.args:
                if isinstance(arg, parse.PatternVar):
                    if arg.name.startswith('C') or arg.typ is int:
                        args.append("ConstInt(%s)" % self.bindings[arg.name])
                    else:
                        args.append(self.bindings[arg.name])
                elif isinstance(arg, parse.PatternConst):
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
            self.visit(p)

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

    def visit_Terminal(self, ast):
        if len(ast.rules) == 0:
            return
        def _add_binding(pattern, path, name):
            while path:
                el = path[0]
                path = path[1:]
                if el == 'C':
                    assert pattern.matches_constant()
                else:
                    opname, index = el
                    assert isinstance(pattern, parse.PatternOp)
                    assert pattern.opname == opname
                    pattern = pattern.args[index]
            bindings[pattern] = name
        for rule in ast.rules:
            bindings = {}
            intbound_bindings = {}
            for path, name in ast.bindings.iteritems():
                _add_binding(rule.pattern, path, name)
            self.bindings = bindings
            self.intbound_bindings = intbound_bindings
            self.generate_rule(rule, self.method_opname, self.name_positions[rule.name], self.method_boxnames, self.method_boundnames)

    def visit_IsConstMatcher(self, ast):
        currlevel = self.level
        self.emit_stacking_condition("b_%s.is_constant()" % ast.name)
        self.emit("%s = b_%s.get_constant_int()" % (ast.constname, ast.name))
        self.visit(ast.ifyes)
        self.level = currlevel
        if ast.ifno:
            with self.emit_indent("else:"):
                self.visit(ast.ifno)
        if ast.nextmatcher:
            self.visit(ast.nextmatcher)

    def visit_OpMatcher(self, ast):
        currlevel = self.level
        boxname = "%s_%s" % (ast.name, ast.opname)
        self.emit(
            "%s = self.optimizer.as_operation(%s, rop.%s)"
            % (boxname, ast.name, ast.opname.upper())
        )
        self.emit_stacking_condition("%s is not None" % boxname)
        boxnames, boundnames = self._emit_arg_reads(ast.name, boxname, len(ast.argnames))
        assert boxnames == ast.argnames
        self.visit(ast.ifyes)
        self.level = currlevel
        if ast.ifno:
            with self.emit_indent("else:"):
                self.visit(ast.ifno)
        if ast.nextmatcher:
            self.visit(ast.nextmatcher)

    def generate_method(self, opname, rules):
        all_rules = []
        for rule in rules:
            all_rules.extend(generate_commutative_rules(rule))

        name_positions = {}
        names = []
        for rule in all_rules:
            if rule.name not in name_positions:
                name_positions[rule.name] = len(name_positions)
                names.append(rule.name)
        self.name_positions = name_positions
        self.method_opname = opname
        self.emit("_rule_names_%s = %r" % (opname, names))
        self.emit("_rule_fired_%s = [0] * %s" % (opname, len(names)))
        self.emit("_all_rules_fired.append((%r, _rule_names_%s, _rule_fired_%s))" % (opname, opname, opname))
        with self.emit_indent("def optimize_%s(self, op):" % opname.upper()):
            numargs = len(rules[0].pattern.args)
            boxnames, boundnames = self._emit_arg_reads("arg", "op", numargs)
            self.method_boxnames = boxnames
            self.method_boundnames = boundnames
            for subset_rules in split_by_result_type(all_rules):
                subset_rules = sort_rules(subset_rules)
                if not subset_rules:
                    continue
                matcher = create_matcher(subset_rules)
                self.visit(matcher)
                #for rule in subset_rules:
                #    self.generate_rule(rule, opname, , boxnames, boundnames)
            self.emit("return self.emit(op)")

    def generate_rule(self, rule, opname, position, boxnames, boundnames):
        self.emit("# %s: %s => %s" % (rule.name, rule.pattern, rule.target))
        currlevel = self.level
        checks = []
        self._pattern_arg_check(boxnames, boundnames, rule.pattern.args)
        for el in rule.elements:
            self.visit(el)
        self.generate_target(rule.target)
        self.emit("self._rule_fired_%s[%s] += 1" % (opname, position))
        self.emit("return")
        self.level = currlevel

    def visit_Compute(self, el):
        if el.expr.typ is IntBound:
            self.intbound_bindings[el.name] = el.name
        else:
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
        return "%s.%s" % (self.intbound_bindings[expr.varname], expr.attrname)

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
            with self.emit_indent("def _eq(self, box1, bound1, box2, bound2):"):
                self.emit("if box1 is box2: return True")
                self.emit("if bound1.is_constant() and bound2.is_constant() and bound1.lower == bound2.lower: return True")
                self.emit("return False")
            self.emit("_all_rules_fired = []")
            return self.generate_code(ast)

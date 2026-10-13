import ast
from contextlib import contextmanager
from collections import defaultdict

from rpython.jit.metainterp.ruleopt import ir, parse
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

class IRCodegen(parse.Visitor):
    """Build method-body IR; developed alongside Codegen during migration."""

    def __init__(self, self_value, op_value, bindings, intbound_bindings=None):
        self.self_ref = ir.Ref(self_value)
        self.op_ref = ir.Ref(op_value)
        # DSL variable names map to IR Values, rather than Python name strings.
        self.bindings = bindings
        self.intbound_bindings = (
            {} if intbound_bindings is None else intbound_bindings)
        # Matcher-generated names (arg_0, b_arg_0, C_arg_0, ...) map to Values.
        # Terminal lowering will connect these to each rule's DSL names.
        self.matcher_values = {}
        self.block = ir.Block([])

    def default_visit(self, expr):
        raise NotImplementedError("lower expression: %r" % (expr,))

    def emit(self, stmt):
        self.block.statements.append(stmt)

    @contextmanager
    def matcher_branch(self, block):
        outer_block = self.block
        outer_values = self.matcher_values
        self.block = block
        self.matcher_values = self.matcher_values.copy()
        try:
            yield
        finally:
            self.block = outer_block
            self.matcher_values = outer_values

    def visit_IsConstMatcher(self, matcher):
        bound = ir.Ref(self.matcher_values['b_' + matcher.name])
        cond = ir.Call(ir.Attribute(bound, 'is_constant'), [])
        then_block = ir.Block([])
        else_block = ir.Block([])
        cond = ir.If(cond, then_block, else_block)
        self.emit(cond)
        with self.matcher_branch(then_block):
            constvalue = ir.Value(matcher.constname)
            const = ir.Call(ir.Attribute(bound, 'get_constant_int'), [])
            self.emit(ir.Bind(constvalue, const))
            self.matcher_values[matcher.constname] = constvalue
            self.visit(matcher.ifyes)
        if matcher.ifno:
            with self.matcher_branch(else_block):
                self.visit(matcher.ifno)
        if matcher.nextmatcher:
            self.visit(matcher.nextmatcher)

    def visit_OpMatcher(self, matcher):
        box = ir.Ref(self.matcher_values[matcher.name])
        matched = ir.Value("%s_%s" % (matcher.name, matcher.opname))
        lookup = ir.Call(
            ir.Attribute(ir.Attribute(self.self_ref, "optimizer"), "as_operation"),
            [box, ir.Attribute(ir.Symbol("rop"), matcher.opname.upper())])
        self.emit(ir.Bind(matched, lookup))
        then_block = ir.Block([])
        else_block = ir.Block([])
        condition = ir.Binary("is not", ir.Ref(matched), ir.Literal(None))
        self.emit(ir.If(condition, then_block, else_block))
        with self.matcher_branch(then_block):
            boxes, bounds = self.emit_arg_reads(
                ir.Ref(matched), len(matcher.argnames), prefix=matcher.name)
            for name, box_value, bound_value in zip(matcher.argnames, boxes, bounds):
                self.matcher_values[name] = box_value
                self.matcher_values["b_" + name] = bound_value
            self.visit(matcher.ifyes)
        if matcher.ifno is not None:
            with self.matcher_branch(else_block):
                self.visit(matcher.ifno)
        if matcher.nextmatcher is not None:
            self.visit(matcher.nextmatcher)

    def emit_arg_reads(self, operation, numargs, prefix="arg"):
        """Bind replaced argument boxes and their bounds; return both lists.

        operation is an IR expression. The returned lists contain Values.
        These are internal matcher values, not yet DSL variable bindings.
        """
        boxes = []
        bounds = []
        for i in range(numargs):
            box = ir.Value("%s_%s" % (prefix, i))
            bound = ir.Value("b_%s_%s" % (prefix, i))
            arg = ir.Call(ir.Attribute(operation, "getarg"), [ir.Literal(i)])
            self.emit(ir.Bind(box, ir.Call(ir.Symbol("get_box_replacement"), [arg])))
            self.emit(ir.Bind(bound, self.self_method("getintbound", ir.Ref(box))))
            boxes.append(box)
            bounds.append(bound)
        return boxes, bounds

    def visit_Number(self, expr):
        return ir.Literal(expr.value)

    def visit_Name(self, expr):
        if expr.name == "LONG_BIT":
            return ir.Symbol(expr.name)
        if expr.typ is IntBound:
            return ir.Ref(self.intbound_bindings[expr.name])
        return ir.Ref(self.value_for(expr.name))

    def visit_Attribute(self, expr):
        bound = ir.Ref(self.intbound_bindings[expr.varname])
        if expr.attrname == 'zeros':
            value = ir.Unary('~', ir.Binary(
                '|', ir.Attribute(bound, 'tvalue'),
                ir.Attribute(bound, 'tmask')))
        else:
            attrname = 'tvalue' if expr.attrname == 'ones' else expr.attrname
            value = ir.Attribute(bound, attrname)
        return ir.Call(ir.Symbol('intmask'), [value])

    def visit_BinOp(self, expr):
        return ir.Binary(expr.pysymbol, self.visit(expr.left),
                         self.visit(expr.right))

    def visit_IntBinOp(self, expr):
        if not expr.need_ruint:
            return self.visit_BinOp(expr)
        r_uint = ir.Symbol('r_uint')
        left = ir.Call(r_uint, [self.visit(expr.left)])
        right = ir.Call(r_uint, [self.visit(expr.right)])
        intmask = ir.Symbol('intmask')
        return ir.Call(intmask, [ir.Binary(expr.pysymbol, left, right)])

    def visit_MethodCall(self, expr):
        receiver = self.visit(expr.value)
        args = [self.visit(arg) for arg in expr.args]
        return ir.Call(ir.Attribute(receiver, expr.methname), args)

    def visit_UnaryOp(self, expr):
        left = self.visit(expr.left)
        if not expr.need_ruint:
            return ir.Unary(expr.pysymbol, left)
        r_uint = ir.Symbol('r_uint')
        intmask = ir.Symbol('intmask')
        left = ir.Call(r_uint, [left])
        res = ir.Unary(expr.pysymbol, left)
        return ir.Call(intmask, [res])

    def visit_FuncCall(self, expr):
        args = [self.visit(arg) for arg in expr.args]
        return ir.Call(ir.Symbol(expr.funcname), args)

    def generate_rule_body(self, rule, opname, position):
        comment = "%s: %s => %s" % (rule.name, rule.pattern, rule.target)
        finish = ir.FinishRule(self.self_ref, opname, position, comment)
        self.generate_body(rule.elements, rule.target, finish)

    def generate_body(self, elements, target, finish=None):
        """Append a rule's computations, checks and target action.

        Optionally finish with the rule counter and return. Pattern matching
        is handled separately.
        self.block is the insertion point; checks move it into their true arm.
        """
        outer_block = self.block
        outer_bindings = self.bindings
        outer_intbound_bindings = self.intbound_bindings
        self.bindings = self.bindings.copy()
        self.intbound_bindings = self.intbound_bindings.copy()
        try:
            for element in elements:
                self.visit(element)
            self.generate_target(target)
            if finish is not None:
                self.emit(finish)
        finally:
            self.block = outer_block
            self.bindings = outer_bindings
            self.intbound_bindings = outer_intbound_bindings

    def visit_Compute(self, element):
        value = ir.Value(element.name)
        self.emit(ir.Bind(value, self.visit(element.expr)))
        if element.expr.typ is IntBound:
            self.intbound_bindings[element.name] = value
        else:
            self.bindings[element.name] = value

    def visit_Check(self, element):
        then = ir.Block([])
        cond = ir.If(self.visit(element.expr), then, ir.Block([]))
        self.emit(cond)
        self.block = then

    def value_for(self, varname):
        return self.bindings[varname]

    def self_method(self, name, *args, **kwargs):
        kwargs = [(key, value) for key, value in kwargs.iteritems()]
        return ir.Call(ir.Attribute(self.self_ref, name), list(args), kwargs)

    def constant_expr(self, target):
        if target.const in ("MININT", "MAXINT", "LONG_BIT"):
            return ir.Symbol(target.const)
        return ir.Literal(ast.literal_eval(target.const))

    def target_box(self, target):
        """An operation argument must be a box, including for integer values."""
        if isinstance(target, parse.PatternVar):
            value = ir.Ref(self.value_for(target.name))
            if target.typ is int:
                return ir.Call(ir.Symbol("ConstInt"), [value])
            return value
        if isinstance(target, parse.PatternConst):
            return ir.Call(ir.Symbol("ConstInt"), [self.constant_expr(target)])
        raise NotImplementedError("lower target argument: %r" % (target,))

    def generate_target(self, target):
        # generate_rule owns the rule counter and return, after this action.
        if isinstance(target, parse.PatternVar):
            value = self.target_box(target)
            call = self.self_method("make_equal_to", self.op_ref, value)
            self.emit(ir.ExprStmt(call))
            return
        if isinstance(target, parse.PatternConst):
            value = self.constant_expr(target)
            call = self.self_method("make_constant_int", self.op_ref, value)
            self.emit(ir.ExprStmt(call))
            return
        if isinstance(target, parse.PatternOp):
            call = self.self_method(
                "replace_op_with", self.op_ref,
                ir.Attribute(ir.Symbol('rop'), target.opname.upper()),
                args=ir.ListExpr([
                    self.target_box(element) for element in target.args]))
            newop = ir.Value('newop')
            self.emit(ir.Bind(newop, call))
            call2 = ir.Call(
                ir.Attribute(ir.Attribute(self.self_ref, 'optimizer'),
                             'send_extra_operation'),
                [ir.Ref(newop)])
            self.emit(ir.ExprStmt(call2))
            return
        raise NotImplementedError("lower target: %r" % (target,))


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
        attrname = expr.attrname
        varname = self.intbound_bindings[expr.varname]
        if expr.attrname == 'ones':
            attrname = 'tvalue'
        if expr.attrname == 'zeros':
            return "intmask(~(%s.tvalue | %s.tmask))" % (varname, varname)
        return "intmask(%s.%s)" % (varname, attrname)

    def visit_Number(self, expr, prec=0):
        return str(expr.value)

    def visit_UnaryOp(self, expr, prec=0):
        sub_prec = expr.precedence
        sub = self.visit(expr.left, sub_prec + 1)
        if expr.need_ruint:
            return "intmask(%sr_uint(%s))" % (expr.pysymbol, sub)
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

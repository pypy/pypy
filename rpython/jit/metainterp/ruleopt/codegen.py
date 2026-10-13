import ast
from contextlib import contextmanager
from collections import defaultdict

from rpython.jit.metainterp.ruleopt import ir, iropt, parse
from rpython.jit.metainterp.ruleopt.emit import emit_python
from rpython.jit.metainterp.optimizeopt.intutils import IntBound

commutative_ops = {"int_add", "int_mul", "int_and", "int_mul", "int_or",
                   "int_xor", "int_eq", "int_ne"}


def boxed_constant_name(target):
    """Name of a prebuilt box for a literal or a machine-word constant."""
    if target.const in ("MININT", "MAXINT", "LONG_BIT"):
        return "CONST_" + target.const
    value = ast.literal_eval(target.const)
    if value == 0:
        return "CONST_FALSE"
    if value == 1:
        return "CONST_TRUE"
    if value < 0:
        return "CONST_INT_NEG_%d" % -value
    return "CONST_INT_%d" % value


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

def find_reusable_operation(pattern, target, path=()):
    """Return the path to a proper operation subtree equal to target, or None.

    Paths use Terminal.bindings' ((opname, argument_index), ...) convention.
    Search depth first, in argument order, excluding the root operation.
    This compares pattern syntax only; the caller must ensure that target
    variables still refer to their original pattern bindings.
    """
    def matches(a, b):
        if type(a) is not type(b):
            return False
        if isinstance(a, parse.PatternOp):
            if a.opname != b.opname:
                return False
            if all(matches(child1, child2) for child1, child2 in zip(a.args, b.args)):
                return True
            if a.opname in commutative_ops:
                assert len(a.args) == len(b.args) == 2
                if all(matches(child1, child2) for child1, child2 in zip(a.args, b.args[::-1])):
                    return True
            return False
        if isinstance(a, parse.PatternVar):
            return a.name == b.name
        if isinstance(a, parse.PatternConst):
            return a.const == b.const
        return False
    if matches(pattern, target) and path:
        return path
    if isinstance(pattern, parse.PatternOp) and isinstance(target, parse.PatternOp):
        for i, sub in enumerate(pattern.args):
            res = find_reusable_operation(sub, target, path + ((pattern.opname, i), ))
            if res is not None:
                return res
    return None


class IRCodegen(parse.Visitor):
    """Lower matcher trees and rules to optimizer method-body IR."""

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
        self.method_opname = None
        self.name_positions = {}
        self.rule_names = []
        self.block = ir.Block([])

    def generate_method(self, opname, rules):
        """Build one optimizer method body using a fresh IRCodegen instance."""
        all_rules = []
        for rule in rules:
            all_rules.extend(generate_commutative_rules(rule))
        self.method_opname = opname
        for rule in all_rules:
            if rule.name not in self.name_positions:
                self.name_positions[rule.name] = len(self.rule_names)
                self.rule_names.append(rule.name)

        numargs = len(rules[0].pattern.args)
        boxes, bounds = self.emit_arg_reads(self.op_ref, numargs)
        for i, (box, bound) in enumerate(zip(boxes, bounds)):
            self.matcher_values["arg_%s" % i] = box
            self.matcher_values["b_arg_%s" % i] = bound
        for subset_rules in split_by_result_type(all_rules):
            subset_rules = sort_rules(subset_rules)
            if not subset_rules:
                continue
            matcher = create_matcher(subset_rules)
            self.visit(matcher)
        self.emit(ir.Return(self.self_method('emit', self.op_ref)))
        return self.block

    def default_visit(self, expr):
        raise NotImplementedError("lower expression: %r" % (expr,))

    def emit(self, stmt):
        self.block.statements.append(stmt)

    def emit_condition(self, condition):
        then_block = ir.Block([])
        self.emit(ir.If(condition, then_block, ir.Block([])))
        self.block = then_block

    def match_variable(self, pattern, matcher_name):
        """Bind a DSL variable or check a repeated occurrence.

        matcher_name identifies a box, or an extracted integer for C variables.
        The terminal visitor will resolve the pattern's path to this name.
        """
        value = self.matcher_values[matcher_name]
        if pattern.name.startswith('C'):
            if pattern.name not in self.bindings:
                self.bindings[pattern.name] = value
                return
            binding = self.bindings[pattern.name]
            if binding is value:
                return
            cond = ir.Binary('==', ir.Ref(value), ir.Ref(binding))
            self.emit_condition(cond)
            return
        bound_value = self.matcher_values['b_' + matcher_name]
        if pattern.name not in self.bindings:
            self.bindings[pattern.name] = value
            self.intbound_bindings[pattern.name] = bound_value
            return
        binding = self.bindings[pattern.name]
        bound_binding = self.intbound_bindings[pattern.name]
        if binding is value:
            return
        call = self.self_method('_eq', ir.Ref(value), ir.Ref(bound_value), ir.Ref(binding), ir.Ref(bound_binding))
        self.emit_condition(call)

    def match_pattern(self, pattern, path_bindings, path=()):
        """Walk a rule pattern after structural matching has succeeded.

        path_bindings is Terminal.bindings: paths map to matcher names.
        Each operation argument extends the path by ((opname, index),).
        Constant leaves use a further ('C',) suffix for the extracted integer.
        """
        if isinstance(pattern, parse.PatternOp):
            for index, arg in enumerate(pattern.args):
                child_path = path + ((pattern.opname, index),)
                self.match_pattern(arg, path_bindings, child_path)
            return
        if isinstance(pattern, parse.PatternVar):
            if pattern.name.startswith('C'):
                path = path + ('C', )
            name = path_bindings[path]
            self.match_variable(pattern, name)
            return
        if isinstance(pattern, parse.PatternConst):
            value = self.matcher_values[path_bindings[path + ('C', )]]
            cond = ir.Binary('==', ir.Ref(value), self.constant_expr(pattern))
            self.emit_condition(cond)
            return
        raise NotImplementedError("walk terminal pattern")

    def visit_Terminal(self, terminal):
        outer_block = self.block
        outer_bindings = self.bindings
        outer_intbound_bindings = self.intbound_bindings
        try:
            for rule in terminal.rules:
                # Every candidate starts at the same insertion point, outside
                # any conditions emitted for the previous candidate.
                self.block = outer_block
                self.bindings = {}
                self.intbound_bindings = {}
                self.match_pattern(rule.pattern, terminal.bindings)
                reused_value = None
                # Exercise: find_reusable_operation gives a path, if any.
                # Resolve it through terminal.bindings (path -> name) and
                # self.matcher_values (name -> Value) to set reused_value.
                path = find_reusable_operation(rule.pattern, rule.target)
                if path:
                    reused_value = self.matcher_values[terminal.bindings[path]]
                self.generate_rule_body(
                    rule, self.method_opname, self.name_positions[rule.name],
                    reused_value)
        finally:
            self.block = outer_block
            self.bindings = outer_bindings
            self.intbound_bindings = outer_intbound_bindings

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

    def generate_rule_body(self, rule, opname, position, reused_value=None):
        comment = "%s: %s => %s" % (rule.name, rule.pattern, rule.target)
        finish = ir.FinishRule(self.self_ref, opname, position, comment)
        self.generate_body(rule.elements, rule.target, finish, reused_value)

    def generate_body(self, elements, target, finish=None, reused_value=None):
        """Append a rule's computations, checks and target action.

        Optionally finish with the rule counter and return. Pattern matching
        is handled separately.
        self.block is the insertion point; checks move it into their true arm.
        reused_value, if supplied, is a matched box equivalent to the target.
        """
        outer_block = self.block
        outer_bindings = self.bindings
        outer_intbound_bindings = self.intbound_bindings
        self.bindings = self.bindings.copy()
        self.intbound_bindings = self.intbound_bindings.copy()
        try:
            for element in elements:
                self.visit(element)
            if reused_value is None:
                self.generate_target(target)
            else:
                self.emit(ir.ExprStmt(self.self_method(
                    'make_equal_to', self.op_ref, ir.Ref(reused_value))))
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
        self.emit_condition(self.visit(element.expr))

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
            return ir.Symbol(boxed_constant_name(target))
        raise NotImplementedError("lower target argument: %r" % (target,))

    def generate_target(self, target):
        # generate_rule owns the rule counter and return, after this action.
        if isinstance(target, parse.PatternVar):
            value = self.target_box(target)
            call = self.self_method("make_equal_to", self.op_ref, value)
            self.emit(ir.ExprStmt(call))
            return
        if isinstance(target, parse.PatternConst):
            value = self.target_box(target)
            call = self.self_method("make_constant", self.op_ref, value)
            self.emit(ir.ExprStmt(call))
            return
        if isinstance(target, parse.PatternOp):
            assert len(target.args) in (1, 2)
            args = [self.op_ref,
                    ir.Attribute(ir.Symbol('rop'), target.opname.upper())]
            args.extend(self.target_box(element) for element in target.args)
            call = self.self_method(
                "_replace_op_with_%s_and_send" % len(target.args), *args)
            call.side_effects = True  # forwards op and optimizes its replacement
            self.emit(ir.ExprStmt(call))
            return
        raise NotImplementedError("lower target: %r" % (target,))


class Codegen(object):
    """Emit class boilerplate around method bodies lowered through the IR."""

    def __init__(self):
        self.code = []
        self.level = 0

    @contextmanager
    def emit_indent(self, line=None):
        if line is not None:
            self.emit(line)
        self.level += 1
        try:
            yield
        finally:
            self.level -= 1

    def emit(self, line=""):
        if self.level == 0 and line.startswith(("def ", "class ")):
            self.code.append("")
        if not line.strip():
            self.code.append("")
        else:
            self.code.append("    " * self.level + line)

    def generate_method(self, opname, rules):
        builder = IRCodegen(ir.Value("self"), ir.Value("op"), {})
        body = builder.generate_method(opname, rules)
        iropt.optimize(body)
        names = builder.rule_names
        self.emit("_rule_names_%s = %r" % (opname, names))
        self.emit("_rule_fired_%s = [0] * %s" % (opname, len(names)))
        self.emit("_all_rules_fired.append((%r, _rule_names_%s, _rule_fired_%s))"
                  % (opname, opname, opname))
        with self.emit_indent("def optimize_%s(self, op):" % opname.upper()):
            for line in emit_python(body).splitlines():
                self.emit(line)

    def generate_code(self, ast):
        per_op = defaultdict(list)
        for rule in ast.rules:
            per_op[rule.pattern.opname].append(rule)
        for opname, rules in per_op.items():
            self.generate_method(opname, rules)
        self.emit()
        return "\n".join(self.code)

    def generate_mixin(self, ast):
        # Module-level boxes become prebuilt objects during translation.
        # Zero and one are imported from history by generate.py.
        constants = {}
        pending = [rule.target for rule in ast.rules]
        while pending:
            target = pending.pop()
            if isinstance(target, parse.PatternOp):
                pending.extend(target.args)
            elif isinstance(target, parse.PatternConst):
                name = boxed_constant_name(target)
                if name not in ("CONST_FALSE", "CONST_TRUE"):
                    constants[name] = target.const
        for name, value in sorted(constants.items()):
            self.emit("%s = ConstInt(%s)" % (name, value))
        with self.emit_indent("class OptIntAutoGenerated(object):"):
            with self.emit_indent("def _eq(self, box1, bound1, box2, bound2):"):
                self.emit("if box1 is box2: return True")
                self.emit("if bound1.is_constant() and bound2.is_constant() and bound1.lower == bound2.lower: return True")
                self.emit("return False")
            self.emit("_all_rules_fired = []")
            return self.generate_code(ast)

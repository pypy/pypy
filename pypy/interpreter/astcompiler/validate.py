"""A visitor to validate an AST object."""

from pypy.interpreter.error import oefmt
from pypy.interpreter.astcompiler import ast
from rpython.tool.pairtype import pair, pairtype
from pypy.interpreter.baseobjspace import W_Root


def validate_ast(space, node):
    node.walkabout(AstValidator(space))


class ValidationError(Exception):
    # Will be seen as a ValueError
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message

class ValidationTypeError(ValidationError):
    # Will be seen as a TypeError
    pass


def expr_context_name(ctx):
    if not 1 <= ctx <= len(ast.expr_context_to_class):
        return '??'
    return ast.expr_context_to_class[ctx - 1].__name__[1:]

def _check_context(expected_ctx, actual_ctx):
    if expected_ctx != actual_ctx:
        raise ValidationError(
            "expression must have %s context but has %s instead" %
            (expr_context_name(expected_ctx), expr_context_name(actual_ctx)))


class __extend__(ast.AST):

    def check_context(self, visitor, ctx):
        raise AssertionError("should only be on expressions")

    def walkabout_with_ctx(self, visitor, ctx):
        self.walkabout(visitor)  # With "load" context.


class __extend__(ast.expr):

    def check_context(self, visitor, ctx):
        if ctx != ast.Load:
            raise ValidationError(
                "expression which can't be assigned to in %s context" %
                expr_context_name(ctx))


class __extend__(ast.Name):

    def check_context(self, visitor, ctx):
        _check_context(ctx, self.ctx)


class __extend__(ast.List):

    def check_context(self, visitor, ctx):
        _check_context(ctx, self.ctx)

    def walkabout_with_ctx(self, visitor, ctx):
        visitor._validate_exprs(self.elts, ctx)


class __extend__(ast.Tuple):

    def check_context(self, visitor, ctx):
        _check_context(ctx, self.ctx)

    def walkabout_with_ctx(self, visitor, ctx):
        visitor._validate_exprs(self.elts, ctx)


class __extend__(ast.Starred):

    def check_context(self, visitor, ctx):
        _check_context(ctx, self.ctx)

    def walkabout_with_ctx(self, visitor, ctx):
        visitor._validate_expr(self.value, ctx)


class __extend__(ast.Subscript):

    def check_context(self, visitor, ctx):
        _check_context(ctx, self.ctx)


class __extend__(ast.Attribute):

    def check_context(self, visitor, ctx):
        _check_context(ctx, self.ctx)


# Recursive function to validate a Constant value.
def validate_constant(space, w_obj):
    if space.is_w(w_obj, space.w_None):
        return
    if space.is_w(w_obj, space.w_Ellipsis):
        return
    w_type = space.type(w_obj)
    if w_type in (space.w_int,
                  space.w_float,
                  space.w_complex,
                  space.w_bool,
                  space.w_unicode,
                  space.w_bytes):
        return
    if w_type in (space.w_tuple, space.w_frozenset):
        for w_item in space.unpackiterable(w_obj):
            validate_constant(space, w_item)
        return
    raise ValidationTypeError("got an invalid type in Constant: %s" %
                              space.type(w_obj).name)


class AstValidator(ast.ASTVisitor):
    def __init__(self, space):
        self.space = space

    def _validate_stmts(self, stmts):
        if not stmts:
            return
        for stmt in stmts:
            if not stmt:
                raise ValidationError("None disallowed in statement list")
            stmt.walkabout(self)

    def _len(self, node):
        if node is None:
            return 0
        return len(node)

    def _validate_expr(self, expr, ctx=ast.Load):
        expr.check_context(self, ctx)
        expr.walkabout_with_ctx(self, ctx)

    def _validate_exprs(self, exprs, ctx=ast.Load, null_ok=False):
        if not exprs:
            return
        for expr in exprs:
            if expr:
                self._validate_expr(expr, ctx)
            elif not null_ok:
                raise ValidationError("None disallowed in expression list")

    def _validate_body(self, body, owner):
        self._validate_nonempty_seq(body, "body", owner)
        self._validate_stmts(body)

    def _validate_nonempty_seq(self, seq, what, owner):
        if not seq:
            raise ValidationError("empty %s on %s" % (what, owner))

    def _validate_nonempty_seq_s(self, seq, what, owner):
        if not seq:
            raise ValidationError("empty %s on %s" % (what, owner))

    def _validate_name(self, name):
        if name in ("None", "True", "False"):
            raise ValidationError("Name node can't be used with '%s' constant" % name)

    def visit_Interactive(self, node):
        self._validate_stmts(node.body)

    def visit_Module(self, node):
        self._validate_stmts(node.body)

    def visit_Expression(self, node):
        self._validate_expr(node.body)

    # Statements

    def visit_arg(self, node):
        if node.annotation:
            self._validate_expr(node.annotation)

    def visit_arguments(self, node):
        self.visit_sequence(node.posonlyargs)
        self.visit_sequence(node.args)
        # XXX py3.5 missing if node.varargannotation:
        # XXX py3.5 missing     if not node.vararg:
        # XXX py3.5 missing         raise ValidationError("varargannotation but no vararg on arguments")
        # XXX py3.5 missing     self._validate_expr(node.varargannotation)
        self.visit_sequence(node.kwonlyargs)
        # XXX py3.5 missing if node.kwargannotation:
        # XXX py3.5 missing     if not node.kwarg:
        # XXX py3.5 missing         raise ValidationError("kwargannotation but no kwarg on arguments")
        # XXX py3.5 missing     self._validate_expr(node.kwargannotation)
        if self._len(node.defaults) > self._len(node.args) + self._len(node.posonlyargs):
            raise ValidationError("more positional defaults than args on arguments")
        if self._len(node.kw_defaults) != self._len(node.kwonlyargs):
            raise ValidationError("length of kwonlyargs is not the same as "
                                  "kw_defaults on arguments")
        self._validate_exprs(node.defaults)
        self._validate_exprs(node.kw_defaults, null_ok=True)

    def visit_FunctionDef(self, node):
        self._validate_body(node.body, "FunctionDef")
        node.args.walkabout(self)
        self._validate_exprs(node.decorator_list)
        if node.returns:
            self._validate_expr(node.returns)

    def visit_AsyncFunctionDef(self, node):
        self._validate_body(node.body, "AsyncFunctionDef")
        node.args.walkabout(self)
        self._validate_exprs(node.decorator_list)
        if node.returns:
            self._validate_expr(node.returns)

    def visit_keyword(self, node):
        self._validate_expr(node.value)

    def visit_ClassDef(self, node):
        self._validate_body(node.body, "ClassDef")
        self._validate_exprs(node.bases)
        self.visit_sequence(node.keywords)
        self._validate_exprs(node.decorator_list)
        # XXX py3.5 missing if node.starargs:
        # XXX py3.5 missing   self._validate_expr(node.starargs)
        # XXX py3.5 missing if node.kwargs:
        # XXX py3.5 missing     self._validate_expr(node.kwargs)

    def visit_Return(self, node):
        if node.value:
            self._validate_expr(node.value)

    def visit_Await(self, node):
        self._validate_expr(node.value)

    def visit_Delete(self, node):
        self._validate_nonempty_seq(node.targets, "targets", "Delete")
        self._validate_exprs(node.targets, ast.Del)

    def visit_Assign(self, node):
        self._validate_nonempty_seq(node.targets, "targets", "Assign")
        self._validate_exprs(node.targets, ast.Store)
        self._validate_expr(node.value)

    def visit_AnnAssign(self, node):
        self._validate_expr(node.target, ast.Store)
        self._validate_expr(node.annotation)
        if node.value:
            self._validate_expr(node.value)

    def visit_AugAssign(self, node):
        self._validate_expr(node.target, ast.Store)
        self._validate_expr(node.value)

    def visit_For(self, node):
        self._validate_expr(node.target, ast.Store)
        self._validate_expr(node.iter)
        self._validate_body(node.body, "For")
        self._validate_stmts(node.orelse)

    def visit_AsyncFor(self, node):
        self._validate_expr(node.target, ast.Store)
        self._validate_expr(node.iter)
        self._validate_body(node.body, "AsyncFor")
        self._validate_stmts(node.orelse)

    def visit_While(self, node):
        self._validate_expr(node.test)
        self._validate_body(node.body, "While")
        self._validate_stmts(node.orelse)

    def visit_If(self, node):
        self._validate_expr(node.test)
        self._validate_body(node.body, "If")
        self._validate_stmts(node.orelse)

    def visit_withitem(self, node):
        self._validate_expr(node.context_expr)
        if node.optional_vars:
            self._validate_expr(node.optional_vars, ast.Store)

    def visit_With(self, node):
        self._validate_nonempty_seq(node.items, "items", "With")
        self.visit_sequence(node.items)
        self._validate_body(node.body, "With")

    def visit_AsyncWith(self, node):
        self._validate_nonempty_seq(node.items, "items", "AsyncWith")
        self.visit_sequence(node.items)
        self._validate_body(node.body, "AsyncWith")

    def visit_Raise(self, node):
        if node.exc:
            self._validate_expr(node.exc)
            if node.cause:
                self._validate_expr(node.cause)
        elif node.cause:
            raise ValidationError("Raise with cause but no exception")

    def visit_Try(self, node):
        self._validate_body(node.body, "Try")
        if not node.handlers and not node.finalbody:
            raise ValidationError(
                "Try has neither except handlers nor finalbody")
        if not node.handlers and node.orelse:
            raise ValidationError(
                "Try has orelse but no except handlers")
        for handler in node.handlers:
            handler.walkabout(self)
        self._validate_stmts(node.orelse)
        self._validate_stmts(node.finalbody)

    def visit_ExceptHandler(self, node):
        if node.type:
            self._validate_expr(node.type)
        self._validate_body(node.body, "ExceptHandler")

    def visit_Assert(self, node):
        self._validate_expr(node.test)
        if node.msg:
            self._validate_expr(node.msg)

    def visit_Import(self, node):
        self._validate_nonempty_seq(node.names, "names", "Import")

    def visit_ImportFrom(self, node):
        if node.level < 0:
            raise ValidationError("Negative ImportFrom level")
        self._validate_nonempty_seq(node.names, "names", "ImportFrom")

    def visit_Global(self, node):
        self._validate_nonempty_seq_s(node.names, "names", "Global")

    def visit_Nonlocal(self, node):
        self._validate_nonempty_seq_s(node.names, "names", "Nonlocal")

    def visit_Expr(self, node):
        self._validate_expr(node.value)

    def visit_Pass(self, node):
        pass

    def visit_Break(self, node):
        pass

    def visit_Continue(self, node):
        pass

    # pattern matching

    def _validate_patterns(self, patterns, star_ok=False):
        if patterns:
            seen_star = False
            for pattern in patterns:
                if star_ok and isinstance(pattern, ast.MatchStar):
                    if seen_star:
                        raise ValidationError("multiple starred names in sequence pattern")
                    self._validate_capture(pattern.name)
                    seen_star = True
                    continue
                pattern.walkabout(self)

    def _validate_capture(self, name):
        if name == "_":
            raise ValidationError("can't capture name '_' in patterns")
        self._validate_name(name)

    def visit_Match(self, node):
        self._validate_nonempty_seq(node.cases, "cases", "Match")
        self._validate_expr(node.subject)
        for case_ in node.cases:
            case_.walkabout(self)

    def visit_match_case(self, node):
        if node.guard:
            self._validate_expr(node.guard)
        self._validate_stmts(node.body)
        node.pattern.walkabout(self)

    def visit_MatchValue(self, node):
        space = self.space
        value = node.value
        self._validate_expr(value)
        if isinstance(value, ast.Constant):
            w_obj = value.value
            w_typ = space.type(w_obj)
            if (space.is_w(w_typ, space.w_int) or
                    space.is_w(w_typ, space.w_float) or
                    space.is_w(w_typ, space.w_unicode) or
                    space.is_w(w_typ, space.w_bytes) or
                    space.is_w(w_typ, space.w_complex)):
                return
            raise ValidationError("unexpected constant inside of a literal pattern")

    def visit_MatchSingleton(self, node):
        if (not self.space.is_w(node.value, self.space.w_True) and
                not self.space.is_w(node.value, self.space.w_False) and
                not self.space.is_w(node.value, self.space.w_None)):
            raise ValidationError(
                "MatchSingleton can only contain True, False and None")

    def visit_MatchSequence(self, node):
        self._validate_patterns(node.patterns, star_ok=True)

    def visit_MatchMapping(self, node):
        if node.keys and node.patterns and len(node.keys) != len(node.patterns):
            raise ValidationError("MatchMapping doesn't have the same number of keys as patterns")
        for key in node.keys:
            if isinstance(key, ast.Constant):
                continue
            if not isinstance(key, ast.Attribute):
                raise ValidationError("can only have Constant or Attribute in the keys of a MatchMapping")
        if node.rest is not None:
            self._validate_capture(node.rest)
        self._validate_patterns(node.keys)

    def visit_MatchClass(self, node):
        if len(node.kwd_attrs) != len(node.kwd_patterns):
            raise ValidationError("MatchClass doesn't have the same number of keyword attributes as patterns")
        self._validate_expr(node.cls)
        cls = node.cls
        while 1:
            if isinstance(cls, ast.Name):
                break
            if isinstance(cls, ast.Attribute):
                # recurse
                cls = cls.value
            else:
                raise ValidationError("MatchClass cls field can only contain Name or Attribute nodes.")
        for name in node.kwd_attrs:
            self._validate_name(name)
        self._validate_patterns(node.patterns)
        self._validate_patterns(node.kwd_patterns)

    def visit_MatchStar(self, node):
        raise ValidationError("can't use MatchStar here")

    def visit_MatchAs(self, node):
        if node.name:
            self._validate_capture(node.name)
        if node.pattern:
            if not node.name:
                raise ValidationError("MatchAs must specify a target name if a pattern is given")
            node.pattern.walkabout(self)

    def visit_MatchOr(self, node):
        if len(node.patterns) < 2:
            raise ValidationError("MatchOr requires at least 2 patterns")
        self._validate_patterns(node.patterns)

    # Expressions

    def visit_Name(self, node):
        self._validate_name(node.id)

    def visit_Constant(self, node):
        validate_constant(self.space, node.value)

    def visit_BoolOp(self, node):
        if self._len(node.values) < 2:
            raise ValidationError("BoolOp with less than 2 values")
        self._validate_exprs(node.values)

    def visit_UnaryOp(self, node):
        self._validate_expr(node.operand)

    def visit_BinOp(self, node):
        self._validate_expr(node.left)
        self._validate_expr(node.right)

    def visit_Lambda(self, node):
        node.args.walkabout(self)
        self._validate_expr(node.body)

    def visit_IfExp(self, node):
        self._validate_expr(node.test)
        self._validate_expr(node.body)
        self._validate_expr(node.orelse)

    def visit_Dict(self, node):
        if self._len(node.keys) != self._len(node.values):
            raise ValidationError(
                "Dict doesn't have the same number of keys as values")
        self._validate_exprs(node.keys, null_ok=True)
        self._validate_exprs(node.values)

    def visit_Set(self, node):
        self._validate_exprs(node.elts)

    def _validate_comprehension(self, generators):
        if not generators:
            raise ValidationError("comprehension with no generators")
        for comp in generators:
            assert isinstance(comp, ast.comprehension)
            self._validate_expr(comp.target, ast.Store)
            self._validate_expr(comp.iter)
            self._validate_exprs(comp.ifs)

    def visit_ListComp(self, node):
        self._validate_comprehension(node.generators)
        self._validate_expr(node.elt)

    def visit_SetComp(self, node):
        self._validate_comprehension(node.generators)
        self._validate_expr(node.elt)

    def visit_GeneratorExp(self, node):
        self._validate_comprehension(node.generators)
        self._validate_expr(node.elt)

    def visit_DictComp(self, node):
        self._validate_comprehension(node.generators)
        self._validate_expr(node.key)
        self._validate_expr(node.value)

    def visit_Yield(self, node):
        if node.value:
            self._validate_expr(node.value)

    def visit_YieldFrom(self, node):
        self._validate_expr(node.value)

    def visit_Compare(self, node):
        if not node.comparators:
            raise ValidationError("Compare with no comparators")
        if len(node.comparators) != len(node.ops):
            raise ValidationError("Compare has a different number "
                                  "of comparators and operands")
        self._validate_exprs(node.comparators)
        self._validate_expr(node.left)

    def visit_Call(self, node):
        self._validate_expr(node.func)
        self._validate_exprs(node.args)
        self.visit_sequence(node.keywords)
        # XXX py3.5 missing if node.starargs:
        # XXX py3.5 missing     self._validate_expr(node.starargs)
        # XXX py3.5 missing if node.kwargs:
        # XXX py3.5 missing     self._validate_expr(node.kwargs)

    def visit_Attribute(self, node):
        self._validate_expr(node.value)

    def visit_Subscript(self, node):
        self._validate_expr(node.value)
        self._validate_expr(node.slice)

    def visit_RevDBMetaVar(self, node):
        pass

    # Subscripts
    def visit_Slice(self, node):
        if node.lower:
            self._validate_expr(node.lower)
        if node.upper:
            self._validate_expr(node.upper)
        if node.step:
            self._validate_expr(node.step)

    def visit_JoinedStr(self, node):
        self._validate_exprs(node.values)

    def visit_FormattedValue(self, node):
        self._validate_expr(node.value)
        if node.format_spec:
            self._validate_expr(node.format_spec)

    def visit_NamedExpr(self, node):
        self._validate_expr(node.target, ast.Store)
        self._validate_expr(node.value)

    def visit_FunctionType(self, node):
        self._validate_exprs(node.argtypes)
        self._validate_expr(node.returns)

    def visit_Starred(self, node):
        self._validate_expr(node.value)


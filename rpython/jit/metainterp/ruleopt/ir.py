"""Tree IR for generated matching code.

Nodes describe code; constructing them does not execute that code.
Value objects identify bindings independently of their eventual printed names.
"""


class Node(object):
    def iter_children(self):
        """Iterate direct syntax children in source order.

        Value identities in Ref and Bind are not syntax children. Both If
        branches are included; this describes structure, not execution.
        """
        return iter(())

    def walk(self, cls=None):
        """Yield self, then recursively visit children in source order.

        Exercise: use iter_children() and each child's walk(). Visit shared
        expressions once per occurrence, without a visited set. Treat the
        tree as read-only while iterating.
        """
        if cls is None or isinstance(self, cls):
            yield self
        for child in self.iter_children():
            for node in child.walk():
                if cls is None or isinstance(node, cls):
                    yield node

    def as_dot(self):
        """Return a Graphviz graph of this subtree, preserving shared nodes."""
        from rpython.jit.metainterp.ruleopt.irview import as_dot
        return as_dot(self)

    def view(self):
        """Inspect this subtree in dotviewer (also handy from a debugger)."""
        from dotviewer.graphpage import GraphPage
        page = GraphPage()
        page.source = self.as_dot()
        page.links = {}
        page.display()


class Value(Node):
    def __init__(self, name_hint):
        self.name_hint = name_hint

    def __repr__(self):
        return "Value(%r)" % (self.name_hint,)


class Expr(Node):
    # A promise made by lowering: evaluation may be discarded if unused.
    # This is not permission to move the expression or reuse its result.
    side_effects = False

    def has_side_effects(self):
        """Include effects from evaluating child expressions.
        """
        return any(call.side_effects for call in self.walk(Call))

    def __repr__(self):
        return "%s()" % type(self).__name__


class Ref(Expr):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return "Ref(%r)" % (self.value,)


class Literal(Expr):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return "Literal(%r)" % (self.value,)


class Symbol(Expr):
    """An external Python name, which must not be renamed like a local Value."""

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "Symbol(%r)" % (self.name,)


class Attribute(Expr):
    def __init__(self, obj, name):
        self.obj = obj
        self.name = name

    def iter_children(self):
        yield self.obj

    def __repr__(self):
        return "Attribute(%r, %r)" % (self.obj, self.name)


class Call(Expr):
    def __init__(self, function, args, keywords=None, side_effects=False):
        assert isinstance(args, list), "Call args must be a list"
        self.function = function
        self.args = args
        # A list of (name, expression) pairs preserves evaluation order.
        self.keywords = [] if keywords is None else keywords
        self.side_effects = side_effects

    def iter_children(self):
        yield self.function
        for arg in self.args:
            yield arg
        for name, expr in self.keywords:
            yield expr

    def __repr__(self):
        effects = ", side_effects=True" if self.side_effects else ""
        return "Call(%r, %r, %r%s)" % (
            self.function, self.args, self.keywords, effects)


class ListExpr(Expr):
    def __init__(self, items):
        self.items = items

    def iter_children(self):
        return iter(self.items)

    def __repr__(self):
        return "ListExpr(%r)" % (self.items,)


class Unary(Expr):
    def __init__(self, operator, operand):
        self.operator = operator
        self.operand = operand

    def iter_children(self):
        yield self.operand

    def __repr__(self):
        return "Unary(%r, %r)" % (self.operator, self.operand)


class Binary(Expr):
    def __init__(self, operator, left, right):
        self.operator = operator
        self.left = left
        self.right = right

    def iter_children(self):
        yield self.left
        yield self.right

    def __repr__(self):
        return "Binary(%r, %r, %r)" % (
            self.operator, self.left, self.right)


class Stmt(Node):
    def __repr__(self):
        return "%s()" % type(self).__name__


class Bind(Stmt):
    def __init__(self, value, expr):
        assert isinstance(value, Value)
        self.value = value
        self.expr = expr

    def iter_children(self):
        yield self.expr

    def __repr__(self):
        return "Bind(%r, %r)" % (self.value, self.expr)


class ExprStmt(Stmt):
    """Evaluate an expression for its effects, discarding its result."""

    def __init__(self, expr):
        self.expr = expr

    def iter_children(self):
        yield self.expr

    def __repr__(self):
        return "ExprStmt(%r)" % (self.expr,)


class Return(Stmt):
    def __init__(self, expr=None):
        self.expr = expr

    def iter_children(self):
        if self.expr is not None:
            yield self.expr

    def __repr__(self):
        return "Return(%r)" % (self.expr,)


class FinishRule(Stmt):
    """Record a successful rewrite and return from the generated method."""

    def __init__(self, self_ref, opname, rule_index, comment):
        self.self_ref = self_ref
        self.opname = opname
        self.rule_index = rule_index
        self.comment = comment

    def iter_children(self):
        yield self.self_ref

    def __repr__(self):
        return "FinishRule(%r, %r, %r, %r)" % (
            self.self_ref, self.opname, self.rule_index, self.comment)


class If(Stmt):
    def __init__(self, condition, then_block, else_block):
        self.condition = condition
        self.then_block = then_block
        self.else_block = else_block

    def iter_children(self):
        yield self.condition
        yield self.then_block
        yield self.else_block

    def __repr__(self):
        return "If(%r, %r, %r)" % (
            self.condition, self.then_block, self.else_block)


class Block(Node):
    def __init__(self, statements):
        self.statements = statements

    def iter_children(self):
        return iter(self.statements)

    def __repr__(self):
        return "Block(%r)" % (self.statements,)

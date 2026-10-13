"""Tree IR for generated matching code.

Nodes describe code; constructing them does not execute that code.
Value objects identify bindings independently of their eventual printed names.
"""


class Value(object):
    def __init__(self, name_hint):
        self.name_hint = name_hint

    def __repr__(self):
        return "Value(%r)" % (self.name_hint,)


class Expr(object):
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

    def __repr__(self):
        return "Attribute(%r, %r)" % (self.obj, self.name)


class Call(Expr):
    def __init__(self, function, args, keywords=None):
        assert isinstance(args, list), "Call args must be a list"
        self.function = function
        self.args = args
        # A list of (name, expression) pairs preserves evaluation order.
        self.keywords = [] if keywords is None else keywords

    def __repr__(self):
        return "Call(%r, %r, %r)" % (
            self.function, self.args, self.keywords)


class ListExpr(Expr):
    def __init__(self, items):
        self.items = items

    def __repr__(self):
        return "ListExpr(%r)" % (self.items,)


class Unary(Expr):
    def __init__(self, operator, operand):
        self.operator = operator
        self.operand = operand

    def __repr__(self):
        return "Unary(%r, %r)" % (self.operator, self.operand)


class Binary(Expr):
    def __init__(self, operator, left, right):
        self.operator = operator
        self.left = left
        self.right = right

    def __repr__(self):
        return "Binary(%r, %r, %r)" % (
            self.operator, self.left, self.right)


class Stmt(object):
    def __repr__(self):
        return "%s()" % type(self).__name__


class Bind(Stmt):
    def __init__(self, value, expr):
        assert isinstance(value, Value)
        self.value = value
        self.expr = expr

    def __repr__(self):
        return "Bind(%r, %r)" % (self.value, self.expr)


class ExprStmt(Stmt):
    """Evaluate an expression for its effects, discarding its result."""

    def __init__(self, expr):
        self.expr = expr

    def __repr__(self):
        return "ExprStmt(%r)" % (self.expr,)


class Return(Stmt):
    def __init__(self, expr=None):
        self.expr = expr

    def __repr__(self):
        return "Return(%r)" % (self.expr,)


class If(Stmt):
    def __init__(self, condition, then_block, else_block):
        self.condition = condition
        self.then_block = then_block
        self.else_block = else_block

    def __repr__(self):
        return "If(%r, %r, %r)" % (
            self.condition, self.then_block, self.else_block)


class Block(object):
    def __init__(self, statements):
        self.statements = statements

    def __repr__(self):
        return "Block(%r)" % (self.statements,)

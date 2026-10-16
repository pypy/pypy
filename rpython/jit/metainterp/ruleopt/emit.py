"""Print method-body IR as Python source, without optimizing it."""

from contextlib import contextmanager
from numbers import Number

from rpython.jit.metainterp.ruleopt import ir


# Same precedence ordering as parse.precedence_classes, with 'not' and 'is'
# included for the code IR. Keep the printer independent of the DSL parser.
COMPARISONS = ("==", "!=", "<", "<=", ">", ">=", "is", "is not")
BINARY_PRECEDENCE = {}
for precedence, operators in enumerate([
        ("or",), ("and",), (), COMPARISONS,
        ("|",), ("^",), ("&",), ("<<", ">>"),
        ("+", "-"), ("*", "//", "/", "%")]):
    for operator in operators:
        BINARY_PRECEDENCE[operator] = precedence
UNARY_PRECEDENCE = {"not": 2, "-": 10, "+": 10, "~": 10}
CALL_PRECEDENCE = 11


class PythonEmitter(object):
    def __init__(self):
        self.level = 0
        self.lines = []
        self.names = {}
        self.used_names = set()

    def emit(self, line):
        if not line.strip():
            self.lines.append("")
        else:
            self.lines.append("    " * self.level + line)

    @contextmanager
    def emit_indent(self, line=None):
        if line is not None:
            self.emit(line)
        self.level += 1
        yield
        self.level -= 1

    def name_for(self, value):
        if value not in self.names:
            name = value.name_hint
            suffix = 1
            while name in self.used_names:
                name = "%s_v%s" % (value.name_hint, suffix)
                suffix += 1
            self.names[value] = name
            self.used_names.add(name)
        return self.names[value]

    def reserve_symbols(self, node):
        # Reserve external names before assigning any local names, including
        # symbols encountered later in the body or inside a nested branch.
        for symbol in node.walk(ir.Symbol):
            self.used_names.add(symbol.name)

    def emit_expr(self, expr, prec=0):
        if isinstance(expr, ir.Symbol):
            return expr.name
        if isinstance(expr, ir.Literal):
            result = repr(expr.value)
            # A negative literal is syntactically a unary expression.
            if result.startswith("-") and prec > UNARY_PRECEDENCE["-"]:
                result = "(" + result + ")"
            return result
        if isinstance(expr, ir.Ref):
            return self.name_for(expr.value)
        if isinstance(expr, ir.ListExpr):
            return "[%s]" % ", ".join(self.emit_expr(item) for item in expr.items)
        if isinstance(expr, ir.Attribute):
            receiver = self.emit_expr(expr.obj, CALL_PRECEDENCE)
            # Numeric literals need lexical separation from the attribute dot:
            # 42.real is invalid Python, even though literals bind tightly.
            if (isinstance(expr.obj, ir.Literal) and
                    isinstance(expr.obj.value, Number) and
                    not isinstance(expr.obj.value, bool) and
                    not receiver.startswith("(")):
                receiver = "(" + receiver + ")"
            return "%s.%s" % (receiver, expr.name)
        if isinstance(expr, ir.Call):
            args = [self.emit_expr(arg) for arg in expr.args]
            for name, expression in expr.keywords:
                args.append("%s=%s" % (name, self.emit_expr(expression)))
            return "%s(%s)" % (
                self.emit_expr(expr.function, CALL_PRECEDENCE), ", ".join(args))
        if isinstance(expr, ir.Unary):
            sub_prec = UNARY_PRECEDENCE[expr.operator]
            sub = self.emit_expr(expr.operand, sub_prec + 1)
            separator = " " if expr.operator == "not" else ""
            result = "%s%s%s" % (expr.operator, separator, sub)
            if prec > sub_prec:
                result = "(" + result + ")"
            return result
        if isinstance(expr, ir.Binary):
            sub_prec = BINARY_PRECEDENCE[expr.operator]
            left_prec = sub_prec
            right_prec = sub_prec + 1  # left associative, as in codegen
            # Unlike arithmetic, comparisons chain in Python. Parenthesize
            # either nested comparison to preserve the IR's binary semantics.
            if expr.operator in COMPARISONS:
                left_prec += 1
            left = self.emit_expr(expr.left, left_prec)
            right = self.emit_expr(expr.right, right_prec)
            result = "%s %s %s" % (left, expr.operator, right)
            if prec > sub_prec:
                result = "(" + result + ")"
            return result
        raise NotImplementedError("unsupported expression: %r" % (expr,))

    def emit_stmt(self, stmt):
        if isinstance(stmt, ir.FinishRule):
            for line in stmt.comment.splitlines():
                self.emit("# " + line)
            receiver = self.emit_expr(stmt.self_ref, CALL_PRECEDENCE)
            self.emit("%s._rule_fired_%s[%s] += 1" % (
                receiver, stmt.opname, stmt.rule_index))
            self.emit("return")
            return
        if isinstance(stmt, ir.ExprStmt):
            self.emit(self.emit_expr(stmt.expr))
            return
        if isinstance(stmt, ir.Bind):
            self.emit("%s = %s" % (self.name_for(stmt.value), self.emit_expr(stmt.expr)))
            return
        if isinstance(stmt, ir.Return):
            if stmt.expr is not None:
                self.emit("return %s" % self.emit_expr(stmt.expr))
            else:
                self.emit("return")
            return
        if isinstance(stmt, ir.If):
            with self.emit_indent("if %s:" % self.emit_expr(stmt.condition)):
                self.emit_block(stmt.then_block)
            if stmt.else_block and stmt.else_block.statements:
                with self.emit_indent("else:"):
                    self.emit_block(stmt.else_block)
            return
        raise NotImplementedError("unsupported statement: %r" % (stmt,))

    def emit_block(self, block):
        if not block.statements:
            self.emit("pass")
            return
        for stmt in block.statements:
            self.emit_stmt(stmt)


def emit_python(block):
    emitter = PythonEmitter()
    emitter.reserve_symbols(block)
    emitter.emit_block(block)
    return "\n".join(emitter.lines)

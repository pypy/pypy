from rpython.rlib.rutf8 import Utf8StringBuilder
from pypy.interpreter.error import oefmt
from pypy.interpreter.astcompiler import ast


PRIORITY_TEST = 0                   # 'if'-'else', 'lambda'
PRIORITY_OR = 1                     # 'or'
PRIORITY_AND = 2                    # 'and'
PRIORITY_NOT = 3                    # 'not'
PRIORITY_CMP = 4                    # '<', '>', '==', '>=', '<=', '!=',
                                    #   'in', 'not in', 'is', 'is not'
PRIORITY_EXPR = 5
PRIORITY_BOR = PRIORITY_EXPR = 6    # '|'
PRIORITY_BXOR = 7                   # '^'
PRIORITY_BAND = 8                   # '&'
PRIORITY_SHIFT = 9                  # '<<', '>>'
PRIORITY_ARITH = 10                 # '+', '-'
PRIORITY_TERM = 11                  # '*', '@', '/', '%', '//'
PRIORITY_FACTOR = 12                # unary '+', '-', '~'
PRIORITY_POWER = 13                 # '**'
PRIORITY_AWAIT = 14                 # 'await'
PRIORITY_ATOM = 15

class Parenthesizer(object):
    def __init__(self, visitor, priority):
        self.visitor = visitor
        self.priority = priority

    def __enter__(self):
        visitor = self.visitor
        level = visitor.level
        if level > self.priority:
            visitor.append_ascii("(")

    def __exit__(self, *args):
        visitor = self.visitor
        level = visitor.level
        if level > self.priority:
            visitor.append_ascii(")")



class UnparseVisitor(ast.ASTVisitor):
    def __init__(self, space):
        self.space = space
        self.builder = Utf8StringBuilder()
        self.level = PRIORITY_TEST

    def maybe_parenthesize(self, priority):
        return Parenthesizer(self, priority)

    def append_w_str(self, w_s):
        s, l = self.space.utf8_len_w(w_s)
        self.builder.append_utf8(s, l)

    def append_ascii(self, s):
        self.builder.append_utf8(s, len(s))

    def append_expr(self, node, priority):
        level = self.level
        self.level = priority
        try:
            node.walkabout(self)
        finally:
            self.level = level

    def default_visitor(self, node):
        raise oefmt(self.space.w_SystemError,
                    "%T is not an expression", node)

    def visit_Num(self, node):
        w_str = self.space.str(node.n)
        self.append_w_str(w_str)

    def visit_Str(self, node):
        w_str = self.space.repr(node.s)
        self.append_w_str(w_str)

    def visit_Bytes(self, node):
        w_str = self.space.repr(node.s)
        self.append_w_str(w_str)

    def visit_Name(self, node):
        self.builder.append(node.id)

    def visit_UnaryOp(self, node):
        op = node.op
        if op == ast.Invert:
            priority = PRIORITY_FACTOR
            op = "~"
        elif op == ast.Not:
            priority = PRIORITY_NOT
            op = "not "
        elif op == ast.UAdd:
            priority = PRIORITY_FACTOR
            op = "+"
        elif op == ast.USub:
            priority = PRIORITY_FACTOR
            op = "-"
        else:
            raise oefmt(self.space.w_SystemError,
                        "unknown unary operator")
        with self.maybe_parenthesize(priority):
            self.append_ascii(op)
            self.append_expr(node.operand, priority)

    def visit_BinOp(self, node):
        right_associative = False
        op = node.op
        if op == ast.Add:
            op = " + "
            priority = PRIORITY_ARITH
        elif op == ast.Sub:
            op = " - "
            priority = PRIORITY_ARITH
        elif op == ast.Mult:
            op = " * "
            priority = PRIORITY_TERM
        elif op == ast.MatMult:
            op = " @ "
            priority = PRIORITY_TERM
        elif op == ast.Div:
            op = " / "
            priority = PRIORITY_TERM
        elif op == ast.FloorDiv:
            op = " // "
            priority = PRIORITY_TERM
        elif op == ast.Mod:
            op = " % "
            priority = PRIORITY_TERM
        elif op == ast.LShift:
            op = " << "
            priority = PRIORITY_SHIFT
        elif op == ast.RShift:
            op = " >> "
            priority = PRIORITY_SHIFT
        elif op == ast.BitOr:
            op = " | "
            priority = PRIORITY_BOR
        elif op == ast.BitXor:
            op = " ^ "
            priority = PRIORITY_BXOR
        elif op == ast.BitAnd:
            op = " & "
            priority = PRIORITY_BAND
        elif op == ast.Pow:
            op = " ** "
            priority = PRIORITY_POWER
            right_associative = True
        else:
            raise oefmt(self.space.w_SystemError,
                        "unknown unary operator")
        with self.maybe_parenthesize(priority):
            self.append_expr(node.left, priority + right_associative)
            self.append_ascii(op)
            self.append_expr(node.right, priority + (not right_associative))
            
    def visit_BoolOp(self, node):
        if node.op == ast.And:
            op = " and "
            priority = PRIORITY_AND
        else:
            op = " or "
            priority = PRIORITY_OR
        with self.maybe_parenthesize(priority):
            for i, value in enumerate(node.values):
                if i > 0:
                    self.append_ascii(op)
                self.append_expr(value, priority + 1)

    def visit_Compare(self, node):
        with self.maybe_parenthesize(PRIORITY_CMP):
            self.append_expr(node.left, PRIORITY_CMP + 1)
            for i in range(len(node.comparators)):
                op = node.ops[i]
                value = node.comparators[i]
                if op == ast.Eq:
                    op = " == "
                elif op == ast.NotEq:
                    op = " != "
                elif op == ast.Lt:
                    op = " < "
                elif op == ast.LtE:
                    op = " <= "
                elif op == ast.Gt:
                    op = " > "
                elif op == ast.GtE:
                    op = " >= "
                elif op == ast.Is:
                    op = " is "
                elif op == ast.IsNot:
                    op = " is not "
                elif op == ast.In:
                    op = " in "
                elif op == ast.NotIn:
                    op = " not in "
                else:
                    raise oefmt(self.space.w_SystemError,
                                "unknown comparator")
                self.append_ascii(op)
                self.append_expr(value, PRIORITY_CMP + 1)


    def visit_IfExp(self, node):
        with self.maybe_parenthesize(PRIORITY_TEST):
            self.append_expr(node.body, PRIORITY_TEST + 1)
            self.append_ascii(" if ")
            self.append_expr(node.test, PRIORITY_TEST + 1)
            self.append_ascii(" else ")
            self.append_expr(node.orelse, PRIORITY_TEST + 1)



def unparse(space, ast):
    visitor = UnparseVisitor(space)
    ast.walkabout(visitor)
    return visitor.builder.build()

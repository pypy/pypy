from rpython.rlib.rutf8 import Utf8StringBuilder
from pypy.interpreter.error import oefmt
from pypy.interpreter.astcompiler import ast

PRIORITY_TUPLE = 0
PRIORITY_TEST = 1                   # 'if'-'else', 'lambda'
PRIORITY_OR = 2                     # 'or'
PRIORITY_AND = 3                    # 'and'
PRIORITY_NOT = 4                    # 'not'
PRIORITY_CMP = 5                    # '<', '>', '==', '>=', '<=', '!=',
                                    #   'in', 'not in', 'is', 'is not'
PRIORITY_EXPR = 6
PRIORITY_BOR = PRIORITY_EXPR = 7    # '|'
PRIORITY_BXOR = 8                   # '^'
PRIORITY_BAND = 9                   # '&'
PRIORITY_SHIFT = 10                 # '<<', '>>'
PRIORITY_ARITH = 11                 # '+', '-'
PRIORITY_TERM = 12                  # '*', '@', '/', '%', '//'
PRIORITY_FACTOR = 13                # unary '+', '-', '~'
PRIORITY_POWER = 14                 # '**'
PRIORITY_AWAIT = 15                 # 'await'
PRIORITY_ATOM = 16

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

    def append_utf8(self, s):
        self.builder.append(s)

    def append_expr(self, node, priority=PRIORITY_TEST):
        level = self.level
        self.level = priority
        try:
            node.walkabout(self)
        finally:
            self.level = level

    def append_if_not_first(self, first, s):
        if not first:
            self.append_ascii(s)
        return False

    def default_visitor(self, node):
        raise oefmt(self.space.w_SystemError,
                    "%T is not an expression", node)

    def visit_Ellipsis(self, node):
        self.append_ascii('...')

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

    def visit_List(self, node):
        if node.elts is None:
            self.append_ascii("[]")
            return
        self.append_ascii("[")
        for i, elt in enumerate(node.elts):
            if i > 0:
                self.append_ascii(", ")
            self.append_expr(elt)
        self.append_ascii("]")

    def visit_Tuple(self, node):
        if node.elts is None:
            self.append_ascii("()")
            return
        self.append_ascii("(")
        for i, elt in enumerate(node.elts):
            if i > 0:
                self.append_ascii(", ")
            self.append_expr(elt)
        if len(node.elts) == 1:
            self.append_ascii(",")
        self.append_ascii(")")

    def visit_Set(self, node):
        self.append_ascii("{")
        for i, elt in enumerate(node.elts):
            if i > 0:
                self.append_ascii(", ")
            self.append_expr(elt)
        self.append_ascii("}")

    def visit_Dict(self, node):
        if node.keys is None:
            self.append_ascii("{}")
            return
        self.append_ascii("{")
        for i, key in enumerate(node.keys):
            value = node.values[i]
            if i > 0:
                self.append_ascii(", ")
            if key is not None:
                self.append_expr(key)
                self.append_ascii(": ")
                self.append_expr(value)
            else:
                self.append_ascii("**")
                self.append_expr(value)
        self.append_ascii("}")

    def append_generators(self, generators):
        for generator in generators:
            if generator.is_async:
                self.append_ascii(' async for ')
            else:
                self.append_ascii(' for ')
            self.append_expr(generator.target, PRIORITY_TUPLE)
            self.append_ascii(' in ')
            self.append_expr(generator.iter, PRIORITY_TEST + 1)
            if generator.ifs:
                for if_ in generator.ifs:
                    self.append_ascii(' if ')
                    self.append_expr(if_, PRIORITY_TEST + 1)

    def visit_ListComp(self, node):
        self.append_ascii('[')
        self.append_expr(node.elt)
        self.append_generators(node.generators)
        self.append_ascii(']')

    def visit_GeneratorExp(self, node):
        self.append_ascii('(')
        self.append_expr(node.elt)
        self.append_generators(node.generators)
        self.append_ascii(')')

    def visit_SetComp(self, node):
        self.append_ascii('{')
        self.append_expr(node.elt)
        self.append_generators(node.generators)
        self.append_ascii('}')

    def visit_Subscript(self, node):
        self.append_expr(node.value, PRIORITY_ATOM)
        self.append_ascii('[')
        self.append_expr(node.slice)
        self.append_ascii(']')

    def visit_Index(self, node):
        self.append_expr(node.value)

    def visit_Slice(self, node):
        if node.lower:
            self.append_expr(node.lower)
        self.append_ascii(':')
        if node.upper:
            self.append_expr(node.upper)
        if node.step:
            self.append_ascii(':')
            self.append_expr(node.upper)

    def visit_ExtSlice(self, node):
        for i, slice in enumerate(node.dims):
            if i > 0:
                self.append_ascii(',')
            self.append_expr(slice)

    def visit_Yield(self, node):
        if node.value:
            self.append_ascii("(yield ")
            self.append_expr(node.value)
            self.append_ascii(")")
        else:
            self.append_ascii("(yield)")

    def visit_YieldFrom(self, node):
        self.append_ascii("(yield from ")
        self.append_expr(node.value)
        self.append_ascii(")")

    def visit_Call(self, node):
        self.append_expr(node.func, PRIORITY_ATOM)
        args = node.args
        if (args and len(args) == 1
                and not node.keywords
                and isinstance(args[0], ast.GeneratorExp)):
            self.append_expr(args[0])
            return

        self.append_ascii('(')
        first = True
        if args:
            for i, arg in enumerate(args):
                first = self.append_if_not_first(first, ', ')
                self.append_expr(arg)
        if node.keywords:
            for i, keyword in enumerate(node.keywords):
                first = self.append_if_not_first(first, ', ')
                if keyword.arg is None:
                    self.append_ascii('**')
                else:
                    self.append_utf8(keyword.arg)
                    self.append_ascii('=')
                self.append_expr(keyword.value)
        self.append_ascii(')')

    def visit_Starred(self, node):
        self.append_ascii('*')
        self.append_expr(node.value, PRIORITY_EXPR)

    def visit_arg(self, node):
        self.append_utf8(node.arg)
        if node.annotation:
            # is this reachable? don't think so!
            self.append_ascii(': ')
            self.append_expr(node.annotation)

    def visit_Lambda(self, node):
        with self.maybe_parenthesize(PRIORITY_TEST):
            args = node.args
            if not args.args and not args.vararg and not args.kwarg and not args.kwonlyargs:
                self.append_ascii("lambda: ")
            else:
                self.append_ascii("lambda ")
                first = True
                if args.defaults:
                    default_count = len(args.defaults)
                else:
                    default_count = 0
                if args.args:
                    for i, arg in enumerate(args.args):
                        first = self.append_if_not_first(first, ', ')
                        di = i - (len(args.args) - default_count)
                        self.append_expr(arg)
                        if di >= 0:
                            self.append_ascii('=')
                            self.append_expr(args.defaults[di])
                if args.vararg or args.kwonlyargs:
                    first = self.append_if_not_first(first, ', ')
                    self.append_ascii('*')
                    if args.vararg:
                        self.append_expr(args.vararg)
                if args.kwonlyargs:
                    for i, arg in enumerate(args.kwonlyargs):
                        first = self.append_if_not_first(first, ', ')
                        di = i - (len(args.kwonlyargs) - default_count)
                        self.append_expr(arg)
                        default = args.kw_defaults[i]
                        if default:
                            self.append_ascii('=')
                            self.append_expr(default)
                if args.kwarg:
                    self.append_ascii('**')
                    self.append_expr(args.kwarg)
                self.append_ascii(': ')
            self.append_expr(node.body)

def unparse(space, ast):
    visitor = UnparseVisitor(space)
    ast.walkabout(visitor)
    return visitor.builder.build()

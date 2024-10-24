import sys
from rply import LexerGenerator, LexingError, ParserGenerator, ParsingError
from rply.token import BaseBox
from rpython.jit.metainterp.optimizeopt.intutils import IntBound


# ____________________________________________________________
# lexer

lg = LexerGenerator()

alltokens = []


def addtok(name, regex):
    alltokens.append(name)
    lg.add(name, regex)


def addkeyword(kw):
    addtok(kw.upper(), r"\b" + kw + r"\b")


addkeyword("check")
addkeyword("and")
addkeyword("or")
addkeyword("SORRY_Z3")

addtok("NUMBER", r"[+-]?([1-9]\d*)|0")
addtok("NAME", r"[a-zA-Z_][a-zA-Z_0-9]*")
addtok("LSHIFT", r"[<][<]")
addtok("URSHIFT", r"[>][>]u")
addtok("ARSHIFT", r"[>][>]")
addtok("ARROW", r"=>")
addtok("LPAREN", r"[(]")
addtok("RPAREN", r"[)]")
addtok("COMMA", r"[,]")
addtok("EQUALEQUAL", r"[=][=]")
addtok("NE", r"[!][=]")
addtok("EQUAL", r"[=]")
addtok("COLON", r"[:]")
addtok("DOT", r"[.]")
addtok("GE", r"[>][=]")
addtok("GT", r"[>]")
addtok("LE", r"[<][=]")
addtok("LT", r"[<]")

addtok("PLUS", r"[+]")
addtok("MINUS", r"[-]")
addtok("MUL", r"[*]")
addtok("DIV", r"[/][/]")
addtok("OP_AND", r"[&]")
addtok("OP_OR", r"[|]")
addtok("OP_XOR", r"\^")
addtok("INVERT", r"~")

addtok("NEWLINE", r" *([#].*)?\n")

lg.ignore(r"[ ]")

lexer = lg.build()


# ____________________________________________________________
# AST classes


class Visitor(object):
    def visit(self, ast, *args, **kwargs):
        for typ in type(ast).mro():
            meth = getattr(self, "visit_%s" % typ.__name__, None)
            if meth is not None:
                return meth(ast, *args, **kwargs)
        return self.default_visit(ast, **kwargs)

    def default_visit(self, ast, **kwargs):
        pass


class BaseAst(BaseBox):
    # __metaclass__ = extendabletype
    sourcepos = None
    endsourcepos = None

    def getsourcepos(self):
        return self.sourcepos

    def __eq__(self, other):
        if type(self) != type(other):
            return NotImplemented
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        args = ["%s=%r" % (key, value) for key, value in self.__dict__.items()]
        if len(args) == 1:
            args = [repr(self.__dict__.values()[0])]
        return "%s(%s)" % (
            type(self).__name__,
            ", ".join(args),
        )

    def view(self):
        from rpython.translator.tool.make_dot import DotGen
        from dotviewer import graphclient
        import pytest

        dotgen = DotGen("G")
        self._dot(dotgen)
        p = pytest.ensuretemp("pyparser").join("temp.dot")
        p.write(dotgen.generate(target=None))
        graphclient.display_dot_file(str(p))

    def _dot(self, dotgen):
        arcs = []
        label = [type(self).__name__]
        for key, value in self.__dict__.items():
            if isinstance(value, BaseAst):
                arcs.append((value, key))
                value._dot(dotgen)
            elif isinstance(value, list) and value and isinstance(value[0], BaseAst):
                for index, item in enumerate(value):
                    arcs.append((item, "%s[%s]" % (key, index)))
                    item._dot(dotgen)
            else:
                label.append("%s = %r" % (key, value))
        dotgen.emit_node(str(id(self)), shape="box", label="\n".join(label))
        for target, label in arcs:
            dotgen.emit_edge(str(id(self)), str(id(target)), label)


class File(BaseAst):
    def __init__(self, rules):
        self.rules = rules


class Rule(BaseAst):
    def __init__(self, name, pattern, cantproof, elements, target):
        self.name = name
        self.pattern = pattern
        self.cantproof = cantproof
        self.elements = elements
        self.target = target

    def newpattern(self, pattern):
        res = Rule(self.name, pattern, self.cantproof, self.elements, self.target)
        res.sourcepos = self.sourcepos
        res.endsourcepos = self.endsourcepos
        return res

    def __str__(self):
        lines = [self.name + ": " + str(self.pattern)]
        for el in self.elements:
            lines.append("    " + str(el))
        lines.append("    => " + str(self.target))
        return "\n".join(lines)


class Pattern(BaseAst):
    pass


class PatternVar(Pattern):
    def __init__(self, name, typ=None):
        self.name = name
        self.typ = typ

    def sort_key(self):
        return (2, self.name)

    def matches_constant(self):
        return self.name.startswith("C")

    def __str__(self):
        return self.name


class PatternConst(BaseAst):
    typ = int
    def __init__(self, const):
        self.const = const

    def sort_key(self):
        return (0, self.const)

    def matches_constant(self):
        return True

    def __str__(self):
        return str(self.const)


class PatternOp(BaseAst):
    def __init__(self, opname, args):
        self.opname = opname
        self.args = args

    def newargs(self, args):
        return PatternOp(self.opname, args)

    def matches_constant(self):
        return False

    def sort_key(self):
        return (1, self.opname) + tuple(sorted(arg.sort_key() for arg in self.args))

    def __str__(self):
        return "%s(%s)" % (self.opname, ", ".join([str(arg) for arg in self.args]))


class Compute(BaseAst):
    def __init__(self, name, expr):
        self.name = name
        self.expr = expr

    def __str__(self):
        return "compute %s = %s" % (self.name, self.expr)


class Check(BaseAst):
    def __init__(self, expr):
        self.expr = expr

    def __str__(self):
        return "check %s" % (self.expr,)


class Expression(BaseAst):
    typ = None # can be None, int, bool, IntBound


class Name(Expression):
    def __init__(self, name, typ=None):
        self.name = name
        if typ is None:
            if self.name.startswith('C'):
                self.typ = int
            else:
                self.typ = IntBound
        else:
            self.typ = typ


class Number(Expression):
    typ = int
    def __init__(self, value):
        self.value = value


class BinOp(Expression):
    def __init__(self, left, right):
        self.left = left
        self.right = right


class IntBinOp(BinOp):
    typ = int
    need_ruint = False

class BoolBinOp(BinOp):
    typ = bool


class Add(IntBinOp):
    opname = "int_add"
    pysymbol = "+"
    need_ruint = True


class Sub(IntBinOp):
    opname = "int_sub"
    pysymbol = "-"
    need_ruint = True


class Mul(IntBinOp):
    opname = "int_mul"
    pysymbol = "*"
    need_ruint = True


class Div(IntBinOp):
    opname = None
    pysymbol = "//"


class LShift(IntBinOp):
    opname = "int_lshift"
    pysymbol = "<<"


class URShift(IntBinOp):
    opname = "uint_rshift"
    pysymbol = ">>"
    need_ruint = True


class ARShift(IntBinOp):
    opname = "int_rshift"
    pysymbol = ">>"
    need_ruint = False


class OpAnd(IntBinOp):
    opname = "int_and"
    pysymbol = "&"


class OpOr(IntBinOp):
    opname = "int_or"
    pysymbol = "|"


class OpXor(IntBinOp):
    opname = "int_xor"
    pysymbol = "^"


class Eq(BoolBinOp):
    opname = "int_eq"
    pysymbol = "=="


class Ge(BoolBinOp):
    opname = "int_ge"
    pysymbol = ">="


class Gt(BoolBinOp):
    opname = "int_gt"
    pysymbol = ">"


class Le(BoolBinOp):
    opname = "int_le"
    pysymbol = "<="


class Lt(BoolBinOp):
    opname = "int_lt"
    pysymbol = "<"


class Ne(BoolBinOp):
    opname = "int_ne"
    pysymbol = "!="


class ShortcutAnd(BinOp):
    typ = bool
    pysymbol = "and"


class ShortcutOr(BinOp):
    typ = bool
    pysymbol = "or"


class UnaryOp(Expression):
    def __init__(self, left):
        self.left = left


class IntUnaryOp(UnaryOp):
    typ = int


class Invert(IntUnaryOp):
    opname = "int_invert"
    pysymbol = "~"



class Attribute(BaseAst):
    typ = int
    def __init__(self, varname, attrname):
        self.varname = varname
        self.attrname = attrname


class MethodCall(Expression):
    def __init__(self, value, methname, args):
        self.value = value
        self.methname = methname
        self.args = args


class FuncCall(Expression):
    def __init__(self, funcname, args):
        self.funcname = funcname
        self.args = args


precedence_classes = [
    ShortcutOr,
    ShortcutAnd,
    # NOT,
    (Eq, Ge, Gt, Le, Lt, Ne),
    OpOr,
    OpXor,
    OpAnd,
    (LShift, ARShift, URShift),
    (Add, Sub),
    (Mul, Div),
    Invert,
    (MethodCall, Attribute),
    (Name, Number),
]

for i, tup in enumerate(precedence_classes):
    if not isinstance(tup, tuple):
        tup = (tup, )
    for cls in tup:
        cls.precedence = i

# ____________________________________________________________
# parser

def production(s):
    def wrapper(func):
        def newfunc(p):
            res = func(p)
            if isinstance(res, BaseAst) and res.sourcepos is None:
                sourcepositions = [a.getsourcepos() for a in p if hasattr(a, 'getsourcepos')]
                if sourcepositions:
                    res.sourcepos = sourcepositions[0]
                    res.endsourcepos = sourcepositions[-1]
            return res
        return pg.production(s)(newfunc)
    return wrapper


pg = ParserGenerator(
    alltokens,
    precedence=[
        ("left", ["OR"]),
        ("left", ["AND"]),
        ("left", ["NOT"]),
        ("left", ["EQUALEQUAL", "GE", "GT", "LE", "LT", "NE"]),
        ("left", ["OP_OR"]),
        ("left", ["OP_XOR"]),
        ("left", ["OP_AND"]),
        ("left", ["LSHIFT", "ARSHIFT", "URSHIFT"]),
        ("left", ["PLUS", "MINUS"]),
        ("left", ["MUL", "DIV"]),
        ("left", ["INVERT"]),
        ("left", ["DOT"]),
    ],
)


@production("file : rule | file rule")
def file(p):
    if len(p) == 1:
        return File(p)
    return File(p[0].rules + [p[1]])


@production("newlines : NEWLINE | NEWLINE newlines")
def newlines(p):
    return None


@production("rule : NAME COLON pattern newlines maybesorry elements ARROW pattern newlines")
def rule(p):
    return Rule(p[0].value, p[2], p[4], p[5], p[7])

@production("maybesorry : | SORRY_Z3 newlines")
def maybesorry(p):
    return bool(p)


@production("pattern : NAME")
def pattern_var(p):
    if p[0].value in ("LONG_BIT", "MININT", "MAXINT"):
        return PatternConst(p[0].value)
    return PatternVar(p[0].value)


@production("pattern : NUMBER")
def pattern_const(p):
    return PatternConst(p[0].value)


@production("pattern : NAME LPAREN patternargs RPAREN")
def pattern_op(p):
    return PatternOp(p[0].value, p[2])


@production("patternargs : pattern | pattern COMMA patternargs")
def patternargs(p):
    if len(p) == 1:
        return p
    return [p[0]] + p[2]


@production("elements : | element newlines elements")
def elements(p):
    if len(p) == 0:
        return []
    return [p[0]] + p[2]


@production("element : NAME EQUAL expression")
def compute_element(p):
    return Compute(p[0].value, p[2])


@production("element : CHECK expression")
def check(p):
    return Check(p[1])


@production("expression : NUMBER")
def expression_number(p):
    return Number(int(p[0].getstr()))


@production("expression : NAME")
def expression_name(p):
    return Name(p[0].getstr())


@production("expression : LPAREN expression RPAREN")
def expression_parens(p):
    return p[1]


@production("expression : INVERT expression")
def expression_unary(p):
    return Invert(p[1])


@production("expression : expression PLUS expression")
@production("expression : expression MINUS expression")
@production("expression : expression MUL expression")
@production("expression : expression DIV expression")
@production("expression : expression LSHIFT expression")
@production("expression : expression URSHIFT expression")
@production("expression : expression ARSHIFT expression")
@production("expression : expression AND expression")
@production("expression : expression OR expression")
@production("expression : expression OP_AND expression")
@production("expression : expression OP_OR expression")
@production("expression : expression OP_XOR expression")
@production("expression : expression EQUALEQUAL expression")
@production("expression : expression GE expression")
@production("expression : expression GT expression")
@production("expression : expression LE expression")
@production("expression : expression LT expression")
@production("expression : expression NE expression")
def expression_binop(p):
    left = p[0]
    right = p[2]
    if p[1].gettokentype() == "PLUS":
        return Add(left, right)
    elif p[1].gettokentype() == "MINUS":
        return Sub(left, right)
    elif p[1].gettokentype() == "MUL":
        return Mul(left, right)
    elif p[1].gettokentype() == "DIV":
        return Div(left, right)
    elif p[1].gettokentype() == "LSHIFT":
        return LShift(left, right)
    elif p[1].gettokentype() == "URSHIFT":
        return URShift(left, right)
    elif p[1].gettokentype() == "ARSHIFT":
        return ARShift(left, right)
    elif p[1].gettokentype() == "AND":
        return ShortcutAnd(left, right)
    elif p[1].gettokentype() == "OR":
        return ShortcutOr(left, right)
    elif p[1].gettokentype() == "OP_AND":
        return OpAnd(left, right)
    elif p[1].gettokentype() == "OP_OR":
        return OpOr(left, right)
    elif p[1].gettokentype() == "OP_XOR":
        return OpXor(left, right)
    elif p[1].gettokentype() == "EQUALEQUAL":
        return Eq(left, right)
    elif p[1].gettokentype() == "GE":
        return Ge(left, right)
    elif p[1].gettokentype() == "GT":
        return Gt(left, right)
    elif p[1].gettokentype() == "LE":
        return Le(left, right)
    elif p[1].gettokentype() == "LT":
        return Lt(left, right)
    elif p[1].gettokentype() == "NE":
        return Ne(left, right)
    else:
        raise AssertionError("Oops, this should not be possible!")


@production("expression : expression DOT NAME maybecall")
def attr_or_method(p):
    assert p[1].gettokentype() == "DOT"
    if p[3] is not None:
        return MethodCall(p[0], p[2].value, p[3])
    return Attribute(p[0].name, p[2].value)


@production("expression : NAME LPAREN args RPAREN")
def funccall(p):
    return FuncCall(p[0].value, p[2])


@production("maybecall : | LPAREN args RPAREN")
def methodcall(p):
    if not p:
        return None
    return p[1]


@production("args : | expression | expression COMMA args ")
def args(p):
    if len(p) <= 1:
        return p
    return [p[0], p[2]]


parser = pg.build()


def print_conflicts():
    if parser.lr_table.rr_conflicts:
        print("rr conflicts")
    for rule_num, token, conflict in parser.lr_table.rr_conflicts:
        print(rule_num, token, conflict)

    if parser.lr_table.sr_conflicts:
        print("sr conflicts")
    for rule_num, token, conflict in parser.lr_table.sr_conflicts:
        print(rule_num, token, conflict)


parser = pg.build()
print_conflicts()


def parse(s):
    ast = parser.parse(lexer.lex(s))
    t = TypingVisitor()
    for rule in ast.rules:
        t.visit(rule)
    return ast


# ___________________________________________________________________________
# attach types

INTBOUND_METHODTYPES = {
    "known_eq_const": (IntBound, [int], bool),
    "known_le_const": (IntBound, [int], bool),
    "known_lt_const": (IntBound, [int], bool),
    "known_ge_const": (IntBound, [int], bool),
    "known_gt_const": (IntBound, [int], bool),
    "known_ne": (IntBound, [IntBound], bool),
    "known_nonnegative": (IntBound, [], bool),
    "is_constant": (IntBound, [], bool),
    "is_bool": (IntBound, [], bool),
    "get_constant_int": (IntBound, [], int),
    "lshift_bound_cannot_overflow": (IntBound, [IntBound], bool),
    "and_bound": (IntBound, [IntBound], IntBound),
    "or_bound": (IntBound, [IntBound], IntBound),
    "lshift_bound": (IntBound, [IntBound], IntBound),
    "rshift_bound": (IntBound, [IntBound], IntBound),
    "urshift_bound": (IntBound, [IntBound], IntBound),
}

FUNCTYPES = {
    "highest_bit": ([int], int)
}

class TypeCheckError(Exception):
    def __init__(self, msg, ast):
        self.msg = msg
        self.ast = ast

    def __str__(self):
        return self.msg

    def format(self, sourcelines=None):
        res = ["Type error: %s" % self.msg]
        if self.ast.sourcepos:
            pos = self.ast.sourcepos
            res.append("in line %s" % pos.lineno)
            if sourcelines:
                line = sourcelines.splitlines()[pos.lineno - 1]
                res.append("    " + line)
                res.append("    " + " " * (pos.colno - 1) + "^")
        return "\n".join(res)


class TypingVisitor(Visitor):
    def _must_be_same_typ(self, ast, typ, targettyp):
        if targettyp is not typ:
            raise TypeCheckError("%s must have type %s, got %s" % (ast, targettyp, typ), ast)

    def _error(self, msg, ast):
        raise TypeCheckError(msg, ast)

    def visit_Rule(self, rule):
        self.bindings = {}
        self.visit(rule.pattern, patterndefine=True)
        for el in rule.elements:
            self.visit(el)
        self.visit(rule.target, patterndefine=False)

    def visit_PatternVar(self, ast, patterndefine):
        if patterndefine:
            if ast.name.startswith('C'):
                typ = int
            else:
                typ = IntBound
            if ast.name in self.bindings:
                self._must_be_same_typ(ast, self.bindings[ast.name], typ)
            else:
                self.bindings[ast.name] = typ
                ast.typ = typ
        else:
            if ast.name not in self.bindings:
                self._error("variable %s is not defined" % (repr(ast.name), ), ast)
            typ = self.bindings[ast.name]
            ast.typ = typ
        return typ

    def visit_PatternConst(self, ast, patterndefine):
        return ast.typ

    def visit_PatternOp(self, ast, patterndefine):
        # XXX check that name exists
        for arg in ast.args:
            self.visit(arg, patterndefine=patterndefine)

    def visit_Compute(self, ast):
        if ast.name in self.bindings:
            self._error("%r is already defined" % ast.name, ast)
        self.bindings[ast.name] = self.visit(ast.expr)

    def visit_Check(self, ast):
        typ = self.visit(ast.expr)
        if typ is not bool:
            self._error("expected check expression to return a bool, got %s" % typ.__name__, ast.expr)

    def visit_Expression(self, ast):
        assert 0, "should be unreachable"

    def visit_Name(self, ast):
        if ast.name == "LONG_BIT":
            return int
        if ast.name not in self.bindings:
            self._error("variable %s is not defined" % (repr(ast.name), ), ast)
        typ = self.bindings[ast.name]
        ast.typ = typ
        return typ

    def visit_Number(self, ast):
        return ast.typ

    def visit_IntBinOp(self, ast):
        self._must_be_same_typ(ast.left, int, self.visit(ast.left))
        self._must_be_same_typ(ast.right, int, self.visit(ast.right))
        return int

    def visit_IntUnaryOp(self, ast):
        self._must_be_same_typ(ast.left, int, self.visit(ast.left))
        return int

    def visit_BoolBinOp(self, ast):
        self._must_be_same_typ(ast.left, int, self.visit(ast.left))
        self._must_be_same_typ(ast.right, int, self.visit(ast.right))
        return bool

    def visit_ShortcutAnd(self, ast):
        self._must_be_same_typ(ast.left, bool, self.visit(ast.left))
        self._must_be_same_typ(ast.right, bool, self.visit(ast.right))
        return bool

    def visit_ShortcutOr(self, ast):
        self._must_be_same_typ(ast.left, bool, self.visit(ast.left))
        self._must_be_same_typ(ast.right, bool, self.visit(ast.right))
        return bool

    def visit_MethodCall(self, ast):
        if ast.methname in INTBOUND_METHODTYPES:
            _, argtyps, restyp = INTBOUND_METHODTYPES[ast.methname]
            for arg, typ in zip(ast.args, argtyps):
                hastyp = self.visit(arg)
                self._must_be_same_typ(arg, hastyp, typ)
            ast.typ = restyp
            return restyp
        self._error("unknown method %r" % ast.methname, ast)

    def visit_FuncCall(self, ast):
        if ast.funcname in FUNCTYPES:
            argtyps, restyp = FUNCTYPES[ast.funcname]
            for arg, typ in zip(ast.args, argtyps):
                hastyp = self.visit(arg)
                self._must_be_same_typ(arg, hastyp, typ)
            self.typ = restyp
            return restyp

    def default_visit(self, ast):
        assert ast.typ is not None
        return ast.typ

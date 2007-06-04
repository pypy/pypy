import py
from pypy.rlib.parsing.ebnfparse import parse_ebnf
from pypy.rlib.parsing.regexparse import parse_regex
from pypy.rlib.parsing.lexer import Lexer, DummyLexer
from pypy.rlib.parsing.deterministic import DFA
from pypy.rlib.parsing.tree import Nonterminal, Symbol, RPythonVisitor
from pypy.rlib.parsing.parsing import PackratParser, LazyParseTable, Rule
from pypy.rlib.parsing.regex import StringExpression

def make_regexes():
    regexs = [
        ("VAR", parse_regex("[A-Z_]([a-zA-Z0-9]|_)*|_")),
        ("NUMBER", parse_regex("(0|[1-9][0-9]*)(\.[0-9]+)?")),
        ("IGNORE", parse_regex(
            "[ \\n\\t]|(/\\*[^\\*]*(\\*[^/][^\\*]*)*\\*/)|(%[^\\n]*)")),
        ("ATOM", parse_regex("([a-z]([a-zA-Z0-9]|_)*)|('[^']*')|\[\]|!|\+|\-")),
        ("(", parse_regex("\(")),
        (")", parse_regex("\)")),
        ("[", parse_regex("\[")),
        ("]", parse_regex("\]")),
        (".", parse_regex("\.")),
        ("|", parse_regex("\|")),
    ]
    return zip(*regexs)

basic_rules = [
    Rule('query', [['toplevel_op_expr', '.', 'EOF']]),
    Rule('fact', [['toplevel_op_expr', '.']]),
    Rule('complexterm', [['ATOM', '(', 'toplevel_op_expr', ')'], ['expr']]),
    Rule('expr',
         [['VAR'],
          ['NUMBER'],
          ['+', 'NUMBER'],
          ['-', 'NUMBER'],
          ['ATOM'],
          ['(', 'toplevel_op_expr', ')'],
          ['listexpr'],
          ]),
    Rule('listexpr', [['[', 'listbody', ']']]),
    Rule('listbody',
         [['toplevel_op_expr', '|', 'toplevel_op_expr'],
          ['toplevel_op_expr']])
    ]

# x: term with priority lower than f
# y: term with priority lower or equal than f
# possible types: xf yf xfx xfy yfx yfy fy fx
# priorities: A > B
#
# binaryops
# (1)  xfx:  A -> B f B | B
# (2)  xfy:  A -> B f A | B
# (3)  yfx:  A -> A f B | B
# (4)  yfy:  A -> A f A | B
#
# unaryops
# (5)  fx:   A -> f A | B
# (6)  fy:   A -> f B | B
# (7)  xf:   A -> B f | B
# (8)  yf:   A -> A f | B

def make_default_operations():
    operations = [
         (1200, [("xfx", ["-->", ":-"]),
                 ("fx",  [":-", "?-"])]),
         (1100, [("xfy", [";"])]),
         (1050, [("xfy", ["->"])]),
         (1000, [("xfy", [","])]),
         (900,  [("fy",  ["\\+"]),
                 ("fx",  ["~"])]),
         (700,  [("xfx", ["<", "=", "=..", "=@=", "=:=", "=<", "==", "=\=", ">",
                          ">=", "@<", "@=<", "@>", "@>=", "\=", "\==", "is"])]),
         (600,  [("xfy", [":"])]),
         (500,  [("yfx", ["+", "-", "/\\", "\\/", "xor"]),
                 ( "fx", ["+", "-", "?", "\\"])]),
         (400,  [("yfx", ["*", "/", "//", "<<", ">>", "mod", "rem"])]),
         (200,  [("xfx", ["**"]), ("xfy", ["^"])]),
         ]
    return operations

default_operations = make_default_operations()

import sys
sys.setrecursionlimit(10000)

def make_from_form(form, op, x, y):
    result = []
    for c in form:
        if c == 'x':
            result.append(x)
        if c == 'y':
            result.append(y)
        if c == 'f':
            result.append(op)
    return result

def make_expansion(y, x, allops):
    expansions = []
    for form, ops in allops:
        for op in ops:
            expansion = make_from_form(form, op, x, y)
            expansions.append(expansion)
    expansions.append([x])
    return expansions

def eliminate_immediate_left_recursion(symbol, expansions):
    newsymbol = "extra%s" % (symbol, )
    newexpansions = []
    with_recursion = [expansion for expansion in expansions
                          if expansion[0] == symbol]
    without_recursion = [expansion for expansion in expansions
                              if expansion[0] != symbol]
    expansions = [expansion + [newsymbol] for expansion in without_recursion]
    newexpansions = [expansion[1:] + [newsymbol]
                         for expansion in with_recursion]
    newexpansions.append([])
    return expansions, newexpansions, newsymbol

def make_all_rules(standard_rules, operations=None):
    if operations is None:
        operations = default_operations
    all_rules = standard_rules[:]
    for i in range(len(operations)):
        precedence, allops = operations[i]
        if i == 0:
            y = "toplevel_op_expr"
        else:
            y = "expr%s" % (precedence, )
        if i != len(operations) - 1:
            x = "expr%s" % (operations[i + 1][0], )
        else:
            x = "complexterm"
        expansions = make_expansion(y, x, allops)
        tup = eliminate_immediate_left_recursion(y, expansions)
        expansions, extra_expansions, extra_symbol = tup
        all_rules.append(Rule(extra_symbol, extra_expansions))
        all_rules.append(Rule(y, expansions))
    return all_rules

def add_necessary_regexs(regexs, names, operations=None):
    if operations is None:
        operations = default_operations
    regexs = regexs[:]
    names = names[:]
    for precedence, allops in operations:
        for form, ops in allops:
            for op in ops:
                regexs.insert(-1, StringExpression(op))
                names.insert(-1, "ATOM")
    return regexs, names

class PrologParseTable(LazyParseTable):
    def terminal_equality(self, symbol, input):
        if input.name == "ATOM":
            return symbol == "ATOM" or symbol == input.source
        return symbol == input.name

class PrologPackratParser(PackratParser):
    def __init__(self, rules, startsymbol):
        PackratParser.__init__(self, rules, startsymbol, PrologParseTable,
                               check_for_left_recursion=False)

def make_basic_rules():
    names, regexs = make_regexes()
    return basic_rules, names, regexs

def make_parser(basic_rules, names, regexs):
    real_rules = make_all_rules(basic_rules)
#    for r in real_rules:
#        print r
    regexs, names = add_necessary_regexs(list(regexs), list(names))
    lexer = Lexer(regexs, names, ignore=["IGNORE"])
    parser_fact = PrologPackratParser(real_rules, "fact")
    parser_query = PrologPackratParser(real_rules, "query")
    return lexer, parser_fact, parser_query, basic_rules

def make_all():
    return make_parser(*make_basic_rules())

def make_parser_at_runtime(operations):
    real_rules = make_all_rules(basic_rules, operations)
    parser_fact = PrologPackratParser(real_rules, "fact")
    return parser_fact

def _dummyfunc(arg, tree):
    return parser_fact

def parse_file(s, parser=None, callback=_dummyfunc, arg=None):
    tokens = lexer.tokenize(s)
    lines = []
    line = []
    for tok in tokens:
        line.append(tok)
        if tok.name == ".":
            lines.append(line)
            line = []
    if parser is None:
        parser = parser_fact
    trees = []
    for line in lines:
        tree = parser.parse(line, lazy=False)
        if callback is not None:
            # XXX ugh
            parser = callback(arg, tree)
            if parser is None:
                parser = parser_fact
        trees.append(tree)
    return trees

def parse_query(s):
    tokens = lexer.tokenize(s, eof=True)
    s = parser_query.parse(tokens, lazy=False)

def parse_query_term(s):
    return get_query_and_vars(s)[0]

def get_query_and_vars(s):
    tokens = lexer.tokenize(s, eof=True)
    s = parser_query.parse(tokens, lazy=False)
    builder = TermBuilder()
    query = builder.build(s)
    return query, builder.varname_to_var

class OrderTransformer(object):
    def transform(self, node):
        if isinstance(node, Symbol):
            return node
        children = [c for c in node.children
                        if isinstance(c, Symbol) or (
                            isinstance(c, Nonterminal) and len(c.children))]
        if isinstance(node, Nonterminal):
            if len(children) == 1:
                return Nonterminal(
                    node.symbol, [self.transform(children[0])])
            if len(children) == 2 or len(children) == 3:
                left = children[-2]
                right = children[-1]
                if (isinstance(right, Nonterminal) and
                    right.symbol.startswith("extraexpr")):
                    if len(children) == 2:
                        leftreplacement = self.transform(left)
                    else:
                        leftreplacement = Nonterminal(
                            node.symbol,
                            [self.transform(children[0]),
                             self.transform(left)])
                    children = [leftreplacement,
                                self.transform(right.children[0]),
                                self.transform(right.children[1])]

                    newnode = Nonterminal(node.symbol, children)
                    return self.transform_extra(right, newnode)
            children = [self.transform(child) for child in children]
            return Nonterminal(node.symbol, children)

    def transform_extra(self, extranode, child):
        children = [c for c in extranode.children
                        if isinstance(c, Symbol) or (
                            isinstance(c, Nonterminal) and len(c.children))]
        symbol = extranode.symbol[5:]
        if len(children) == 2:
            return child
        right = children[2]
        assert isinstance(right, Nonterminal)
        children = [child,
                    self.transform(right.children[0]),
                    self.transform(right.children[1])]
        newnode = Nonterminal(symbol, children)
        return self.transform_extra(right, newnode)

class TermBuilder(RPythonVisitor):

    def __init__(self):
        self.varname_to_var = {}

    def build(self, s):
        "NOT_RPYTHON"
        if isinstance(s, list):
            return self.build_many(s)
        return self.build_query(s)

    def build_many(self, trees):
        ot = OrderTransformer()
        facts = []
        for tree in trees:
            s = ot.transform(tree)
            facts.append(self.build_fact(s))
        return facts

    def build_query(self, s):
        ot = OrderTransformer()
        s = ot.transform(s)
        return self.visit(s.children[0])

    def build_fact(self, node):
        self.varname_to_var = {}
        return self.visit(node.children[0])

    def visit(self, node):
        node = self.find_first_interesting(node)
        return self.dispatch(node)

    def general_nonterminal_visit(self, node):
        from pypy.lang.prolog.interpreter.term import Term, Number, Float
        children = []
        name = ""
        for child in node.children:
            if isinstance(child, Symbol):
                name = self.general_symbol_visit(child).name
            else:
                children.append(child)
        children = [self.visit(child) for child in children]
        if len(children) == 1 and (name == "-" or name == "+"):
            if name == "-":
                factor = -1
            else:
                factor = 1
            child = children[0]
            if isinstance(child, Number):
                return Number(factor * child.num)
            if isinstance(child, Float):
                return Float(factor * child.floatval)
        return Term(name, children)

    def build_list(self, node):
        result = []
        while node is not None:
            node = self._build_list(node, result)
        return result

    def _build_list(self, node, result):
        node = self.find_first_interesting(node)
        if isinstance(node, Nonterminal):
            child = node.children[1]
            if (isinstance(child, Symbol) and
                node.children[1].additional_info == ","):
                element = self.visit(node.children[0])
                result.append(element)
                return node.children[2]
        result.append(self.visit(node))

    def find_first_interesting(self, node):
        if isinstance(node, Nonterminal) and len(node.children) == 1:
            return self.find_first_interesting(node.children[0])
        return node

    def general_symbol_visit(self, node):
        from pypy.lang.prolog.interpreter.term import Atom
        if node.additional_info.startswith("'"):
            end = len(node.additional_info) - 1
            assert end >= 0
            name = unescape(node.additional_info[1:end])
        else:
            name = node.additional_info
        return Atom.newatom(name)

    def visit_VAR(self, node):
        from pypy.lang.prolog.interpreter.term import Var
        varname = node.additional_info
        if varname == "_":
            return Var()
        if varname in self.varname_to_var:
            return self.varname_to_var[varname]
        res = Var()
        self.varname_to_var[varname] = res
        return res

    def visit_NUMBER(self, node):
        from pypy.lang.prolog.interpreter.term import Number, Float
        s = node.additional_info
        try:
            return Number(int(s))
        except ValueError:
            return Float(float(s))

    def visit_complexterm(self, node):
        from pypy.lang.prolog.interpreter.term import Term
        name = self.general_symbol_visit(node.children[0]).name
        children = self.build_list(node.children[2])
        return Term(name, children)

    def visit_expr(self, node):
        from pypy.lang.prolog.interpreter.term import Number, Float
        if node.children[0].additional_info == '-':
            result = self.visit(node.children[1])
            if isinstance(result, Number):
                return Number(-result.num)
            elif isinstance(result, Float):
                return Float(-result.floatval)
        return self.visit(node.children[1])

    def visit_listexpr(self, node):
        from pypy.lang.prolog.interpreter.term import Atom, Term
        node = node.children[1]
        if len(node.children) == 1:
            l = self.build_list(node)
            start = Atom.newatom("[]")
        else:
            l = self.build_list(node.children[0])
            start = self.visit(node.children[2])
        l.reverse()
        curr = start
        for elt in l:
            curr = Term(".", [elt, curr])
        return curr


ESCAPES = {
    "\\a": "\a",
    "\\b": "\b",
    "\\f": "\f",
    "\\n": "\n",
    "\\r": "\r",
    "\\t": "\t",
    "\\v": "\v",
    "\\\\":  "\\"
}


def unescape(s):
    if "\\" not in s:
        return s
    result = []
    i = 0
    escape = False
    while i < len(s):
        c = s[i]
        if escape:
            escape = False
            f = "\\" + c
            if f in ESCAPES:
                result.append(ESCAPES[f])
            else:
                result.append(c)
        elif c == "\\":
            escape = True
        else:
            result.append(c)
        i += 1
    return "".join(result)

def get_engine(source):
    from pypy.lang.prolog.interpreter.engine import Engine
    trees = parse_file(source)
    builder = TermBuilder()
    e = Engine()
    for fact in builder.build_many(trees):
        e.add_rule(fact)
    return e

# generated code between this line and its other occurence

parser_fact = PrologPackratParser([Rule('query', [['toplevel_op_expr', '.', 'EOF']]),
  Rule('fact', [['toplevel_op_expr', '.']]),
  Rule('complexterm', [['ATOM', '(', 'toplevel_op_expr', ')'], ['expr']]),
  Rule('expr', [['VAR'], ['NUMBER'], ['+', 'NUMBER'], ['-', 'NUMBER'], ['ATOM'], ['(', 'toplevel_op_expr', ')'], ['listexpr']]),
  Rule('listexpr', [['[', 'listbody', ']']]),
  Rule('listbody', [['toplevel_op_expr', '|', 'toplevel_op_expr'], ['toplevel_op_expr']]),
  Rule('extratoplevel_op_expr', [[]]),
  Rule('toplevel_op_expr', [['expr1100', '-->', 'expr1100', 'extratoplevel_op_expr'], ['expr1100', ':-', 'expr1100', 'extratoplevel_op_expr'], [':-', 'expr1100', 'extratoplevel_op_expr'], ['?-', 'expr1100', 'extratoplevel_op_expr'], ['expr1100', 'extratoplevel_op_expr']]),
  Rule('extraexpr1100', [[]]),
  Rule('expr1100', [['expr1050', ';', 'expr1100', 'extraexpr1100'], ['expr1050', 'extraexpr1100']]),
  Rule('extraexpr1050', [[]]),
  Rule('expr1050', [['expr1000', '->', 'expr1050', 'extraexpr1050'], ['expr1000', 'extraexpr1050']]),
  Rule('extraexpr1000', [[]]),
  Rule('expr1000', [['expr900', ',', 'expr1000', 'extraexpr1000'], ['expr900', 'extraexpr1000']]),
  Rule('extraexpr900', [[]]),
  Rule('expr900', [['\\+', 'expr900', 'extraexpr900'], ['~', 'expr700', 'extraexpr900'], ['expr700', 'extraexpr900']]),
  Rule('extraexpr700', [[]]),
  Rule('expr700', [['expr600', '<', 'expr600', 'extraexpr700'], ['expr600', '=', 'expr600', 'extraexpr700'], ['expr600', '=..', 'expr600', 'extraexpr700'], ['expr600', '=@=', 'expr600', 'extraexpr700'], ['expr600', '=:=', 'expr600', 'extraexpr700'], ['expr600', '=<', 'expr600', 'extraexpr700'], ['expr600', '==', 'expr600', 'extraexpr700'], ['expr600', '=\\=', 'expr600', 'extraexpr700'], ['expr600', '>', 'expr600', 'extraexpr700'], ['expr600', '>=', 'expr600', 'extraexpr700'], ['expr600', '@<', 'expr600', 'extraexpr700'], ['expr600', '@=<', 'expr600', 'extraexpr700'], ['expr600', '@>', 'expr600', 'extraexpr700'], ['expr600', '@>=', 'expr600', 'extraexpr700'], ['expr600', '\\=', 'expr600', 'extraexpr700'], ['expr600', '\\==', 'expr600', 'extraexpr700'], ['expr600', 'is', 'expr600', 'extraexpr700'], ['expr600', 'extraexpr700']]),
  Rule('extraexpr600', [[]]),
  Rule('expr600', [['expr500', ':', 'expr600', 'extraexpr600'], ['expr500', 'extraexpr600']]),
  Rule('extraexpr500', [['+', 'expr400', 'extraexpr500'], ['-', 'expr400', 'extraexpr500'], ['/\\', 'expr400', 'extraexpr500'], ['\\/', 'expr400', 'extraexpr500'], ['xor', 'expr400', 'extraexpr500'], []]),
  Rule('expr500', [['+', 'expr400', 'extraexpr500'], ['-', 'expr400', 'extraexpr500'], ['?', 'expr400', 'extraexpr500'], ['\\', 'expr400', 'extraexpr500'], ['expr400', 'extraexpr500']]),
  Rule('extraexpr400', [['*', 'expr200', 'extraexpr400'], ['/', 'expr200', 'extraexpr400'], ['//', 'expr200', 'extraexpr400'], ['<<', 'expr200', 'extraexpr400'], ['>>', 'expr200', 'extraexpr400'], ['mod', 'expr200', 'extraexpr400'], ['rem', 'expr200', 'extraexpr400'], []]),
  Rule('expr400', [['expr200', 'extraexpr400']]),
  Rule('extraexpr200', [[]]),
  Rule('expr200', [['complexterm', '**', 'complexterm', 'extraexpr200'], ['complexterm', '^', 'expr200', 'extraexpr200'], ['complexterm', 'extraexpr200']])],
 'fact')
parser_query = PrologPackratParser([Rule('query', [['toplevel_op_expr', '.', 'EOF']]),
  Rule('fact', [['toplevel_op_expr', '.']]),
  Rule('complexterm', [['ATOM', '(', 'toplevel_op_expr', ')'], ['expr']]),
  Rule('expr', [['VAR'], ['NUMBER'], ['+', 'NUMBER'], ['-', 'NUMBER'], ['ATOM'], ['(', 'toplevel_op_expr', ')'], ['listexpr']]),
  Rule('listexpr', [['[', 'listbody', ']']]),
  Rule('listbody', [['toplevel_op_expr', '|', 'toplevel_op_expr'], ['toplevel_op_expr']]),
  Rule('extratoplevel_op_expr', [[]]),
  Rule('toplevel_op_expr', [['expr1100', '-->', 'expr1100', 'extratoplevel_op_expr'], ['expr1100', ':-', 'expr1100', 'extratoplevel_op_expr'], [':-', 'expr1100', 'extratoplevel_op_expr'], ['?-', 'expr1100', 'extratoplevel_op_expr'], ['expr1100', 'extratoplevel_op_expr']]),
  Rule('extraexpr1100', [[]]),
  Rule('expr1100', [['expr1050', ';', 'expr1100', 'extraexpr1100'], ['expr1050', 'extraexpr1100']]),
  Rule('extraexpr1050', [[]]),
  Rule('expr1050', [['expr1000', '->', 'expr1050', 'extraexpr1050'], ['expr1000', 'extraexpr1050']]),
  Rule('extraexpr1000', [[]]),
  Rule('expr1000', [['expr900', ',', 'expr1000', 'extraexpr1000'], ['expr900', 'extraexpr1000']]),
  Rule('extraexpr900', [[]]),
  Rule('expr900', [['\\+', 'expr900', 'extraexpr900'], ['~', 'expr700', 'extraexpr900'], ['expr700', 'extraexpr900']]),
  Rule('extraexpr700', [[]]),
  Rule('expr700', [['expr600', '<', 'expr600', 'extraexpr700'], ['expr600', '=', 'expr600', 'extraexpr700'], ['expr600', '=..', 'expr600', 'extraexpr700'], ['expr600', '=@=', 'expr600', 'extraexpr700'], ['expr600', '=:=', 'expr600', 'extraexpr700'], ['expr600', '=<', 'expr600', 'extraexpr700'], ['expr600', '==', 'expr600', 'extraexpr700'], ['expr600', '=\\=', 'expr600', 'extraexpr700'], ['expr600', '>', 'expr600', 'extraexpr700'], ['expr600', '>=', 'expr600', 'extraexpr700'], ['expr600', '@<', 'expr600', 'extraexpr700'], ['expr600', '@=<', 'expr600', 'extraexpr700'], ['expr600', '@>', 'expr600', 'extraexpr700'], ['expr600', '@>=', 'expr600', 'extraexpr700'], ['expr600', '\\=', 'expr600', 'extraexpr700'], ['expr600', '\\==', 'expr600', 'extraexpr700'], ['expr600', 'is', 'expr600', 'extraexpr700'], ['expr600', 'extraexpr700']]),
  Rule('extraexpr600', [[]]),
  Rule('expr600', [['expr500', ':', 'expr600', 'extraexpr600'], ['expr500', 'extraexpr600']]),
  Rule('extraexpr500', [['+', 'expr400', 'extraexpr500'], ['-', 'expr400', 'extraexpr500'], ['/\\', 'expr400', 'extraexpr500'], ['\\/', 'expr400', 'extraexpr500'], ['xor', 'expr400', 'extraexpr500'], []]),
  Rule('expr500', [['+', 'expr400', 'extraexpr500'], ['-', 'expr400', 'extraexpr500'], ['?', 'expr400', 'extraexpr500'], ['\\', 'expr400', 'extraexpr500'], ['expr400', 'extraexpr500']]),
  Rule('extraexpr400', [['*', 'expr200', 'extraexpr400'], ['/', 'expr200', 'extraexpr400'], ['//', 'expr200', 'extraexpr400'], ['<<', 'expr200', 'extraexpr400'], ['>>', 'expr200', 'extraexpr400'], ['mod', 'expr200', 'extraexpr400'], ['rem', 'expr200', 'extraexpr400'], []]),
  Rule('expr400', [['expr200', 'extraexpr400']]),
  Rule('extraexpr200', [[]]),
  Rule('expr200', [['complexterm', '**', 'complexterm', 'extraexpr200'], ['complexterm', '^', 'expr200', 'extraexpr200'], ['complexterm', 'extraexpr200']])],
 'query')
def recognize(runner, i):
    assert i >= 0
    input = runner.text
    state = 0
    while 1:
        if state == 0:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 0
                return ~i
            if char == '\t':
                state = 1
            elif char == '\n':
                state = 1
            elif char == ' ':
                state = 1
            elif char == '(':
                state = 2
            elif char == ',':
                state = 3
            elif char == '0':
                state = 4
            elif '1' <= char <= '9':
                state = 5
            elif char == '<':
                state = 6
            elif char == '@':
                state = 7
            elif 'A' <= char <= 'Z':
                state = 8
            elif char == '_':
                state = 8
            elif char == '\\':
                state = 9
            elif 'a' <= char <= 'h':
                state = 10
            elif 'j' <= char <= 'l':
                state = 10
            elif 'n' <= char <= 'q':
                state = 10
            elif 's' <= char <= 'w':
                state = 10
            elif char == 'y':
                state = 10
            elif char == 'z':
                state = 10
            elif char == 'x':
                state = 11
            elif char == '|':
                state = 12
            elif char == "'":
                state = 13
            elif char == '+':
                state = 14
            elif char == '/':
                state = 15
            elif char == ';':
                state = 16
            elif char == '?':
                state = 17
            elif char == '[':
                state = 18
            elif char == '*':
                state = 19
            elif char == '.':
                state = 20
            elif char == ':':
                state = 21
            elif char == '>':
                state = 22
            elif char == '^':
                state = 23
            elif char == 'r':
                state = 24
            elif char == '~':
                state = 25
            elif char == '!':
                state = 26
            elif char == '%':
                state = 27
            elif char == ')':
                state = 28
            elif char == '-':
                state = 29
            elif char == '=':
                state = 30
            elif char == ']':
                state = 31
            elif char == 'i':
                state = 32
            elif char == 'm':
                state = 33
            else:
                break
        if state == 4:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 4
                return i
            if char == '.':
                state = 73
            else:
                break
        if state == 5:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 5
                return i
            if char == '.':
                state = 73
            elif '0' <= char <= '9':
                state = 5
                continue
            else:
                break
        if state == 6:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 6
                return i
            if char == '<':
                state = 72
            else:
                break
        if state == 7:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 7
                return ~i
            if char == '=':
                state = 67
            elif char == '<':
                state = 68
            elif char == '>':
                state = 69
            else:
                break
        if state == 8:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 8
                return i
            if '0' <= char <= '9':
                state = 8
                continue
            elif 'A' <= char <= 'Z':
                state = 8
                continue
            elif char == '_':
                state = 8
                continue
            elif 'a' <= char <= 'z':
                state = 8
                continue
            else:
                break
        if state == 9:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 9
                return i
            if char == '=':
                state = 64
            elif char == '/':
                state = 65
            elif char == '+':
                state = 63
            else:
                break
        if state == 10:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 10
                return i
            if '0' <= char <= '9':
                state = 10
                continue
            elif 'A' <= char <= 'Z':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            elif 'a' <= char <= 'z':
                state = 10
                continue
            else:
                break
        if state == 11:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 11
                return i
            if '0' <= char <= '9':
                state = 10
                continue
            elif 'A' <= char <= 'Z':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            elif 'a' <= char <= 'n':
                state = 10
                continue
            elif 'p' <= char <= 'z':
                state = 10
                continue
            elif char == 'o':
                state = 61
            else:
                break
        if state == 13:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 13
                return ~i
            if char == "'":
                state = 26
            elif '\x00' <= char <= '&':
                state = 13
                continue
            elif '(' <= char <= '\xff':
                state = 13
                continue
            else:
                break
        if state == 15:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 15
                return i
            if char == '*':
                state = 57
            elif char == '\\':
                state = 58
            elif char == '/':
                state = 59
            else:
                break
        if state == 17:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 17
                return i
            if char == '-':
                state = 56
            else:
                break
        if state == 18:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 18
                return i
            if char == ']':
                state = 26
            else:
                break
        if state == 19:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 19
                return i
            if char == '*':
                state = 55
            else:
                break
        if state == 21:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 21
                return i
            if char == '-':
                state = 54
            else:
                break
        if state == 22:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 22
                return i
            if char == '=':
                state = 52
            elif char == '>':
                state = 53
            else:
                break
        if state == 24:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 24
                return i
            if '0' <= char <= '9':
                state = 10
                continue
            elif 'A' <= char <= 'Z':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            elif 'a' <= char <= 'd':
                state = 10
                continue
            elif 'f' <= char <= 'z':
                state = 10
                continue
            elif char == 'e':
                state = 50
            else:
                break
        if state == 27:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 27
                return i
            if '\x00' <= char <= '\t':
                state = 27
                continue
            elif '\x0b' <= char <= '\xff':
                state = 27
                continue
            else:
                break
        if state == 29:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 29
                return i
            if char == '>':
                state = 48
            elif char == '-':
                state = 47
            else:
                break
        if state == 30:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 30
                return i
            if char == '@':
                state = 37
            elif char == '<':
                state = 38
            elif char == '.':
                state = 39
            elif char == ':':
                state = 40
            elif char == '=':
                state = 41
            elif char == '\\':
                state = 42
            else:
                break
        if state == 32:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 32
                return i
            if '0' <= char <= '9':
                state = 10
                continue
            elif 'A' <= char <= 'Z':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            elif 'a' <= char <= 'r':
                state = 10
                continue
            elif 't' <= char <= 'z':
                state = 10
                continue
            elif char == 's':
                state = 36
            else:
                break
        if state == 33:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 33
                return i
            if '0' <= char <= '9':
                state = 10
                continue
            elif 'A' <= char <= 'Z':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            elif 'a' <= char <= 'n':
                state = 10
                continue
            elif 'p' <= char <= 'z':
                state = 10
                continue
            elif char == 'o':
                state = 34
            else:
                break
        if state == 34:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 34
                return i
            if '0' <= char <= '9':
                state = 10
                continue
            elif 'A' <= char <= 'Z':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            elif 'a' <= char <= 'c':
                state = 10
                continue
            elif 'e' <= char <= 'z':
                state = 10
                continue
            elif char == 'd':
                state = 35
            else:
                break
        if state == 35:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 35
                return i
            if '0' <= char <= '9':
                state = 10
                continue
            elif 'A' <= char <= 'Z':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            elif 'a' <= char <= 'z':
                state = 10
                continue
            else:
                break
        if state == 36:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 36
                return i
            if '0' <= char <= '9':
                state = 10
                continue
            elif 'A' <= char <= 'Z':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            elif 'a' <= char <= 'z':
                state = 10
                continue
            else:
                break
        if state == 37:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 37
                return ~i
            if char == '=':
                state = 46
            else:
                break
        if state == 39:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 39
                return ~i
            if char == '.':
                state = 45
            else:
                break
        if state == 40:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 40
                return ~i
            if char == '=':
                state = 44
            else:
                break
        if state == 42:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 42
                return ~i
            if char == '=':
                state = 43
            else:
                break
        if state == 47:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 47
                return ~i
            if char == '>':
                state = 49
            else:
                break
        if state == 50:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 50
                return i
            if '0' <= char <= '9':
                state = 10
                continue
            elif 'A' <= char <= 'Z':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            elif 'a' <= char <= 'l':
                state = 10
                continue
            elif 'n' <= char <= 'z':
                state = 10
                continue
            elif char == 'm':
                state = 51
            else:
                break
        if state == 51:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 51
                return i
            if '0' <= char <= '9':
                state = 10
                continue
            elif 'A' <= char <= 'Z':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            elif 'a' <= char <= 'z':
                state = 10
                continue
            else:
                break
        if state == 57:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 57
                return ~i
            if '\x00' <= char <= ')':
                state = 57
                continue
            elif '+' <= char <= '\xff':
                state = 57
                continue
            elif char == '*':
                state = 60
            else:
                break
        if state == 60:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 60
                return ~i
            if '\x00' <= char <= '.':
                state = 57
                continue
            elif '0' <= char <= '\xff':
                state = 57
                continue
            elif char == '/':
                state = 1
            else:
                break
        if state == 61:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 61
                return i
            if '0' <= char <= '9':
                state = 10
                continue
            elif 'A' <= char <= 'Z':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            elif 'a' <= char <= 'q':
                state = 10
                continue
            elif 's' <= char <= 'z':
                state = 10
                continue
            elif char == 'r':
                state = 62
            else:
                break
        if state == 62:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 62
                return i
            if '0' <= char <= '9':
                state = 10
                continue
            elif 'A' <= char <= 'Z':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            elif 'a' <= char <= 'z':
                state = 10
                continue
            else:
                break
        if state == 64:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 64
                return i
            if char == '=':
                state = 66
            else:
                break
        if state == 67:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 67
                return ~i
            if char == '<':
                state = 71
            else:
                break
        if state == 69:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 69
                return i
            if char == '=':
                state = 70
            else:
                break
        if state == 73:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 73
                return ~i
            if '0' <= char <= '9':
                state = 74
            else:
                break
        if state == 74:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 74
                return i
            if '0' <= char <= '9':
                state = 74
                continue
            else:
                break
        runner.last_matched_state = state
        runner.last_matched_index = i - 1
        runner.state = state
        if i == len(input):
            return i
        else:
            return ~i
        break
    runner.state = state
    return ~i
lexer = DummyLexer(recognize, DFA(75,
 {(0, '\t'): 1,
  (0, '\n'): 1,
  (0, ' '): 1,
  (0, '!'): 26,
  (0, '%'): 27,
  (0, "'"): 13,
  (0, '('): 2,
  (0, ')'): 28,
  (0, '*'): 19,
  (0, '+'): 14,
  (0, ','): 3,
  (0, '-'): 29,
  (0, '.'): 20,
  (0, '/'): 15,
  (0, '0'): 4,
  (0, '1'): 5,
  (0, '2'): 5,
  (0, '3'): 5,
  (0, '4'): 5,
  (0, '5'): 5,
  (0, '6'): 5,
  (0, '7'): 5,
  (0, '8'): 5,
  (0, '9'): 5,
  (0, ':'): 21,
  (0, ';'): 16,
  (0, '<'): 6,
  (0, '='): 30,
  (0, '>'): 22,
  (0, '?'): 17,
  (0, '@'): 7,
  (0, 'A'): 8,
  (0, 'B'): 8,
  (0, 'C'): 8,
  (0, 'D'): 8,
  (0, 'E'): 8,
  (0, 'F'): 8,
  (0, 'G'): 8,
  (0, 'H'): 8,
  (0, 'I'): 8,
  (0, 'J'): 8,
  (0, 'K'): 8,
  (0, 'L'): 8,
  (0, 'M'): 8,
  (0, 'N'): 8,
  (0, 'O'): 8,
  (0, 'P'): 8,
  (0, 'Q'): 8,
  (0, 'R'): 8,
  (0, 'S'): 8,
  (0, 'T'): 8,
  (0, 'U'): 8,
  (0, 'V'): 8,
  (0, 'W'): 8,
  (0, 'X'): 8,
  (0, 'Y'): 8,
  (0, 'Z'): 8,
  (0, '['): 18,
  (0, '\\'): 9,
  (0, ']'): 31,
  (0, '^'): 23,
  (0, '_'): 8,
  (0, 'a'): 10,
  (0, 'b'): 10,
  (0, 'c'): 10,
  (0, 'd'): 10,
  (0, 'e'): 10,
  (0, 'f'): 10,
  (0, 'g'): 10,
  (0, 'h'): 10,
  (0, 'i'): 32,
  (0, 'j'): 10,
  (0, 'k'): 10,
  (0, 'l'): 10,
  (0, 'm'): 33,
  (0, 'n'): 10,
  (0, 'o'): 10,
  (0, 'p'): 10,
  (0, 'q'): 10,
  (0, 'r'): 24,
  (0, 's'): 10,
  (0, 't'): 10,
  (0, 'u'): 10,
  (0, 'v'): 10,
  (0, 'w'): 10,
  (0, 'x'): 11,
  (0, 'y'): 10,
  (0, 'z'): 10,
  (0, '|'): 12,
  (0, '~'): 25,
  (4, '.'): 73,
  (5, '.'): 73,
  (5, '0'): 5,
  (5, '1'): 5,
  (5, '2'): 5,
  (5, '3'): 5,
  (5, '4'): 5,
  (5, '5'): 5,
  (5, '6'): 5,
  (5, '7'): 5,
  (5, '8'): 5,
  (5, '9'): 5,
  (6, '<'): 72,
  (7, '<'): 68,
  (7, '='): 67,
  (7, '>'): 69,
  (8, '0'): 8,
  (8, '1'): 8,
  (8, '2'): 8,
  (8, '3'): 8,
  (8, '4'): 8,
  (8, '5'): 8,
  (8, '6'): 8,
  (8, '7'): 8,
  (8, '8'): 8,
  (8, '9'): 8,
  (8, 'A'): 8,
  (8, 'B'): 8,
  (8, 'C'): 8,
  (8, 'D'): 8,
  (8, 'E'): 8,
  (8, 'F'): 8,
  (8, 'G'): 8,
  (8, 'H'): 8,
  (8, 'I'): 8,
  (8, 'J'): 8,
  (8, 'K'): 8,
  (8, 'L'): 8,
  (8, 'M'): 8,
  (8, 'N'): 8,
  (8, 'O'): 8,
  (8, 'P'): 8,
  (8, 'Q'): 8,
  (8, 'R'): 8,
  (8, 'S'): 8,
  (8, 'T'): 8,
  (8, 'U'): 8,
  (8, 'V'): 8,
  (8, 'W'): 8,
  (8, 'X'): 8,
  (8, 'Y'): 8,
  (8, 'Z'): 8,
  (8, '_'): 8,
  (8, 'a'): 8,
  (8, 'b'): 8,
  (8, 'c'): 8,
  (8, 'd'): 8,
  (8, 'e'): 8,
  (8, 'f'): 8,
  (8, 'g'): 8,
  (8, 'h'): 8,
  (8, 'i'): 8,
  (8, 'j'): 8,
  (8, 'k'): 8,
  (8, 'l'): 8,
  (8, 'm'): 8,
  (8, 'n'): 8,
  (8, 'o'): 8,
  (8, 'p'): 8,
  (8, 'q'): 8,
  (8, 'r'): 8,
  (8, 's'): 8,
  (8, 't'): 8,
  (8, 'u'): 8,
  (8, 'v'): 8,
  (8, 'w'): 8,
  (8, 'x'): 8,
  (8, 'y'): 8,
  (8, 'z'): 8,
  (9, '+'): 63,
  (9, '/'): 65,
  (9, '='): 64,
  (10, '0'): 10,
  (10, '1'): 10,
  (10, '2'): 10,
  (10, '3'): 10,
  (10, '4'): 10,
  (10, '5'): 10,
  (10, '6'): 10,
  (10, '7'): 10,
  (10, '8'): 10,
  (10, '9'): 10,
  (10, 'A'): 10,
  (10, 'B'): 10,
  (10, 'C'): 10,
  (10, 'D'): 10,
  (10, 'E'): 10,
  (10, 'F'): 10,
  (10, 'G'): 10,
  (10, 'H'): 10,
  (10, 'I'): 10,
  (10, 'J'): 10,
  (10, 'K'): 10,
  (10, 'L'): 10,
  (10, 'M'): 10,
  (10, 'N'): 10,
  (10, 'O'): 10,
  (10, 'P'): 10,
  (10, 'Q'): 10,
  (10, 'R'): 10,
  (10, 'S'): 10,
  (10, 'T'): 10,
  (10, 'U'): 10,
  (10, 'V'): 10,
  (10, 'W'): 10,
  (10, 'X'): 10,
  (10, 'Y'): 10,
  (10, 'Z'): 10,
  (10, '_'): 10,
  (10, 'a'): 10,
  (10, 'b'): 10,
  (10, 'c'): 10,
  (10, 'd'): 10,
  (10, 'e'): 10,
  (10, 'f'): 10,
  (10, 'g'): 10,
  (10, 'h'): 10,
  (10, 'i'): 10,
  (10, 'j'): 10,
  (10, 'k'): 10,
  (10, 'l'): 10,
  (10, 'm'): 10,
  (10, 'n'): 10,
  (10, 'o'): 10,
  (10, 'p'): 10,
  (10, 'q'): 10,
  (10, 'r'): 10,
  (10, 's'): 10,
  (10, 't'): 10,
  (10, 'u'): 10,
  (10, 'v'): 10,
  (10, 'w'): 10,
  (10, 'x'): 10,
  (10, 'y'): 10,
  (10, 'z'): 10,
  (11, '0'): 10,
  (11, '1'): 10,
  (11, '2'): 10,
  (11, '3'): 10,
  (11, '4'): 10,
  (11, '5'): 10,
  (11, '6'): 10,
  (11, '7'): 10,
  (11, '8'): 10,
  (11, '9'): 10,
  (11, 'A'): 10,
  (11, 'B'): 10,
  (11, 'C'): 10,
  (11, 'D'): 10,
  (11, 'E'): 10,
  (11, 'F'): 10,
  (11, 'G'): 10,
  (11, 'H'): 10,
  (11, 'I'): 10,
  (11, 'J'): 10,
  (11, 'K'): 10,
  (11, 'L'): 10,
  (11, 'M'): 10,
  (11, 'N'): 10,
  (11, 'O'): 10,
  (11, 'P'): 10,
  (11, 'Q'): 10,
  (11, 'R'): 10,
  (11, 'S'): 10,
  (11, 'T'): 10,
  (11, 'U'): 10,
  (11, 'V'): 10,
  (11, 'W'): 10,
  (11, 'X'): 10,
  (11, 'Y'): 10,
  (11, 'Z'): 10,
  (11, '_'): 10,
  (11, 'a'): 10,
  (11, 'b'): 10,
  (11, 'c'): 10,
  (11, 'd'): 10,
  (11, 'e'): 10,
  (11, 'f'): 10,
  (11, 'g'): 10,
  (11, 'h'): 10,
  (11, 'i'): 10,
  (11, 'j'): 10,
  (11, 'k'): 10,
  (11, 'l'): 10,
  (11, 'm'): 10,
  (11, 'n'): 10,
  (11, 'o'): 61,
  (11, 'p'): 10,
  (11, 'q'): 10,
  (11, 'r'): 10,
  (11, 's'): 10,
  (11, 't'): 10,
  (11, 'u'): 10,
  (11, 'v'): 10,
  (11, 'w'): 10,
  (11, 'x'): 10,
  (11, 'y'): 10,
  (11, 'z'): 10,
  (13, '\x00'): 13,
  (13, '\x01'): 13,
  (13, '\x02'): 13,
  (13, '\x03'): 13,
  (13, '\x04'): 13,
  (13, '\x05'): 13,
  (13, '\x06'): 13,
  (13, '\x07'): 13,
  (13, '\x08'): 13,
  (13, '\t'): 13,
  (13, '\n'): 13,
  (13, '\x0b'): 13,
  (13, '\x0c'): 13,
  (13, '\r'): 13,
  (13, '\x0e'): 13,
  (13, '\x0f'): 13,
  (13, '\x10'): 13,
  (13, '\x11'): 13,
  (13, '\x12'): 13,
  (13, '\x13'): 13,
  (13, '\x14'): 13,
  (13, '\x15'): 13,
  (13, '\x16'): 13,
  (13, '\x17'): 13,
  (13, '\x18'): 13,
  (13, '\x19'): 13,
  (13, '\x1a'): 13,
  (13, '\x1b'): 13,
  (13, '\x1c'): 13,
  (13, '\x1d'): 13,
  (13, '\x1e'): 13,
  (13, '\x1f'): 13,
  (13, ' '): 13,
  (13, '!'): 13,
  (13, '"'): 13,
  (13, '#'): 13,
  (13, '$'): 13,
  (13, '%'): 13,
  (13, '&'): 13,
  (13, "'"): 26,
  (13, '('): 13,
  (13, ')'): 13,
  (13, '*'): 13,
  (13, '+'): 13,
  (13, ','): 13,
  (13, '-'): 13,
  (13, '.'): 13,
  (13, '/'): 13,
  (13, '0'): 13,
  (13, '1'): 13,
  (13, '2'): 13,
  (13, '3'): 13,
  (13, '4'): 13,
  (13, '5'): 13,
  (13, '6'): 13,
  (13, '7'): 13,
  (13, '8'): 13,
  (13, '9'): 13,
  (13, ':'): 13,
  (13, ';'): 13,
  (13, '<'): 13,
  (13, '='): 13,
  (13, '>'): 13,
  (13, '?'): 13,
  (13, '@'): 13,
  (13, 'A'): 13,
  (13, 'B'): 13,
  (13, 'C'): 13,
  (13, 'D'): 13,
  (13, 'E'): 13,
  (13, 'F'): 13,
  (13, 'G'): 13,
  (13, 'H'): 13,
  (13, 'I'): 13,
  (13, 'J'): 13,
  (13, 'K'): 13,
  (13, 'L'): 13,
  (13, 'M'): 13,
  (13, 'N'): 13,
  (13, 'O'): 13,
  (13, 'P'): 13,
  (13, 'Q'): 13,
  (13, 'R'): 13,
  (13, 'S'): 13,
  (13, 'T'): 13,
  (13, 'U'): 13,
  (13, 'V'): 13,
  (13, 'W'): 13,
  (13, 'X'): 13,
  (13, 'Y'): 13,
  (13, 'Z'): 13,
  (13, '['): 13,
  (13, '\\'): 13,
  (13, ']'): 13,
  (13, '^'): 13,
  (13, '_'): 13,
  (13, '`'): 13,
  (13, 'a'): 13,
  (13, 'b'): 13,
  (13, 'c'): 13,
  (13, 'd'): 13,
  (13, 'e'): 13,
  (13, 'f'): 13,
  (13, 'g'): 13,
  (13, 'h'): 13,
  (13, 'i'): 13,
  (13, 'j'): 13,
  (13, 'k'): 13,
  (13, 'l'): 13,
  (13, 'm'): 13,
  (13, 'n'): 13,
  (13, 'o'): 13,
  (13, 'p'): 13,
  (13, 'q'): 13,
  (13, 'r'): 13,
  (13, 's'): 13,
  (13, 't'): 13,
  (13, 'u'): 13,
  (13, 'v'): 13,
  (13, 'w'): 13,
  (13, 'x'): 13,
  (13, 'y'): 13,
  (13, 'z'): 13,
  (13, '{'): 13,
  (13, '|'): 13,
  (13, '}'): 13,
  (13, '~'): 13,
  (13, '\x7f'): 13,
  (13, '\x80'): 13,
  (13, '\x81'): 13,
  (13, '\x82'): 13,
  (13, '\x83'): 13,
  (13, '\x84'): 13,
  (13, '\x85'): 13,
  (13, '\x86'): 13,
  (13, '\x87'): 13,
  (13, '\x88'): 13,
  (13, '\x89'): 13,
  (13, '\x8a'): 13,
  (13, '\x8b'): 13,
  (13, '\x8c'): 13,
  (13, '\x8d'): 13,
  (13, '\x8e'): 13,
  (13, '\x8f'): 13,
  (13, '\x90'): 13,
  (13, '\x91'): 13,
  (13, '\x92'): 13,
  (13, '\x93'): 13,
  (13, '\x94'): 13,
  (13, '\x95'): 13,
  (13, '\x96'): 13,
  (13, '\x97'): 13,
  (13, '\x98'): 13,
  (13, '\x99'): 13,
  (13, '\x9a'): 13,
  (13, '\x9b'): 13,
  (13, '\x9c'): 13,
  (13, '\x9d'): 13,
  (13, '\x9e'): 13,
  (13, '\x9f'): 13,
  (13, '\xa0'): 13,
  (13, '\xa1'): 13,
  (13, '\xa2'): 13,
  (13, '\xa3'): 13,
  (13, '\xa4'): 13,
  (13, '\xa5'): 13,
  (13, '\xa6'): 13,
  (13, '\xa7'): 13,
  (13, '\xa8'): 13,
  (13, '\xa9'): 13,
  (13, '\xaa'): 13,
  (13, '\xab'): 13,
  (13, '\xac'): 13,
  (13, '\xad'): 13,
  (13, '\xae'): 13,
  (13, '\xaf'): 13,
  (13, '\xb0'): 13,
  (13, '\xb1'): 13,
  (13, '\xb2'): 13,
  (13, '\xb3'): 13,
  (13, '\xb4'): 13,
  (13, '\xb5'): 13,
  (13, '\xb6'): 13,
  (13, '\xb7'): 13,
  (13, '\xb8'): 13,
  (13, '\xb9'): 13,
  (13, '\xba'): 13,
  (13, '\xbb'): 13,
  (13, '\xbc'): 13,
  (13, '\xbd'): 13,
  (13, '\xbe'): 13,
  (13, '\xbf'): 13,
  (13, '\xc0'): 13,
  (13, '\xc1'): 13,
  (13, '\xc2'): 13,
  (13, '\xc3'): 13,
  (13, '\xc4'): 13,
  (13, '\xc5'): 13,
  (13, '\xc6'): 13,
  (13, '\xc7'): 13,
  (13, '\xc8'): 13,
  (13, '\xc9'): 13,
  (13, '\xca'): 13,
  (13, '\xcb'): 13,
  (13, '\xcc'): 13,
  (13, '\xcd'): 13,
  (13, '\xce'): 13,
  (13, '\xcf'): 13,
  (13, '\xd0'): 13,
  (13, '\xd1'): 13,
  (13, '\xd2'): 13,
  (13, '\xd3'): 13,
  (13, '\xd4'): 13,
  (13, '\xd5'): 13,
  (13, '\xd6'): 13,
  (13, '\xd7'): 13,
  (13, '\xd8'): 13,
  (13, '\xd9'): 13,
  (13, '\xda'): 13,
  (13, '\xdb'): 13,
  (13, '\xdc'): 13,
  (13, '\xdd'): 13,
  (13, '\xde'): 13,
  (13, '\xdf'): 13,
  (13, '\xe0'): 13,
  (13, '\xe1'): 13,
  (13, '\xe2'): 13,
  (13, '\xe3'): 13,
  (13, '\xe4'): 13,
  (13, '\xe5'): 13,
  (13, '\xe6'): 13,
  (13, '\xe7'): 13,
  (13, '\xe8'): 13,
  (13, '\xe9'): 13,
  (13, '\xea'): 13,
  (13, '\xeb'): 13,
  (13, '\xec'): 13,
  (13, '\xed'): 13,
  (13, '\xee'): 13,
  (13, '\xef'): 13,
  (13, '\xf0'): 13,
  (13, '\xf1'): 13,
  (13, '\xf2'): 13,
  (13, '\xf3'): 13,
  (13, '\xf4'): 13,
  (13, '\xf5'): 13,
  (13, '\xf6'): 13,
  (13, '\xf7'): 13,
  (13, '\xf8'): 13,
  (13, '\xf9'): 13,
  (13, '\xfa'): 13,
  (13, '\xfb'): 13,
  (13, '\xfc'): 13,
  (13, '\xfd'): 13,
  (13, '\xfe'): 13,
  (13, '\xff'): 13,
  (15, '*'): 57,
  (15, '/'): 59,
  (15, '\\'): 58,
  (17, '-'): 56,
  (18, ']'): 26,
  (19, '*'): 55,
  (21, '-'): 54,
  (22, '='): 52,
  (22, '>'): 53,
  (24, '0'): 10,
  (24, '1'): 10,
  (24, '2'): 10,
  (24, '3'): 10,
  (24, '4'): 10,
  (24, '5'): 10,
  (24, '6'): 10,
  (24, '7'): 10,
  (24, '8'): 10,
  (24, '9'): 10,
  (24, 'A'): 10,
  (24, 'B'): 10,
  (24, 'C'): 10,
  (24, 'D'): 10,
  (24, 'E'): 10,
  (24, 'F'): 10,
  (24, 'G'): 10,
  (24, 'H'): 10,
  (24, 'I'): 10,
  (24, 'J'): 10,
  (24, 'K'): 10,
  (24, 'L'): 10,
  (24, 'M'): 10,
  (24, 'N'): 10,
  (24, 'O'): 10,
  (24, 'P'): 10,
  (24, 'Q'): 10,
  (24, 'R'): 10,
  (24, 'S'): 10,
  (24, 'T'): 10,
  (24, 'U'): 10,
  (24, 'V'): 10,
  (24, 'W'): 10,
  (24, 'X'): 10,
  (24, 'Y'): 10,
  (24, 'Z'): 10,
  (24, '_'): 10,
  (24, 'a'): 10,
  (24, 'b'): 10,
  (24, 'c'): 10,
  (24, 'd'): 10,
  (24, 'e'): 50,
  (24, 'f'): 10,
  (24, 'g'): 10,
  (24, 'h'): 10,
  (24, 'i'): 10,
  (24, 'j'): 10,
  (24, 'k'): 10,
  (24, 'l'): 10,
  (24, 'm'): 10,
  (24, 'n'): 10,
  (24, 'o'): 10,
  (24, 'p'): 10,
  (24, 'q'): 10,
  (24, 'r'): 10,
  (24, 's'): 10,
  (24, 't'): 10,
  (24, 'u'): 10,
  (24, 'v'): 10,
  (24, 'w'): 10,
  (24, 'x'): 10,
  (24, 'y'): 10,
  (24, 'z'): 10,
  (27, '\x00'): 27,
  (27, '\x01'): 27,
  (27, '\x02'): 27,
  (27, '\x03'): 27,
  (27, '\x04'): 27,
  (27, '\x05'): 27,
  (27, '\x06'): 27,
  (27, '\x07'): 27,
  (27, '\x08'): 27,
  (27, '\t'): 27,
  (27, '\x0b'): 27,
  (27, '\x0c'): 27,
  (27, '\r'): 27,
  (27, '\x0e'): 27,
  (27, '\x0f'): 27,
  (27, '\x10'): 27,
  (27, '\x11'): 27,
  (27, '\x12'): 27,
  (27, '\x13'): 27,
  (27, '\x14'): 27,
  (27, '\x15'): 27,
  (27, '\x16'): 27,
  (27, '\x17'): 27,
  (27, '\x18'): 27,
  (27, '\x19'): 27,
  (27, '\x1a'): 27,
  (27, '\x1b'): 27,
  (27, '\x1c'): 27,
  (27, '\x1d'): 27,
  (27, '\x1e'): 27,
  (27, '\x1f'): 27,
  (27, ' '): 27,
  (27, '!'): 27,
  (27, '"'): 27,
  (27, '#'): 27,
  (27, '$'): 27,
  (27, '%'): 27,
  (27, '&'): 27,
  (27, "'"): 27,
  (27, '('): 27,
  (27, ')'): 27,
  (27, '*'): 27,
  (27, '+'): 27,
  (27, ','): 27,
  (27, '-'): 27,
  (27, '.'): 27,
  (27, '/'): 27,
  (27, '0'): 27,
  (27, '1'): 27,
  (27, '2'): 27,
  (27, '3'): 27,
  (27, '4'): 27,
  (27, '5'): 27,
  (27, '6'): 27,
  (27, '7'): 27,
  (27, '8'): 27,
  (27, '9'): 27,
  (27, ':'): 27,
  (27, ';'): 27,
  (27, '<'): 27,
  (27, '='): 27,
  (27, '>'): 27,
  (27, '?'): 27,
  (27, '@'): 27,
  (27, 'A'): 27,
  (27, 'B'): 27,
  (27, 'C'): 27,
  (27, 'D'): 27,
  (27, 'E'): 27,
  (27, 'F'): 27,
  (27, 'G'): 27,
  (27, 'H'): 27,
  (27, 'I'): 27,
  (27, 'J'): 27,
  (27, 'K'): 27,
  (27, 'L'): 27,
  (27, 'M'): 27,
  (27, 'N'): 27,
  (27, 'O'): 27,
  (27, 'P'): 27,
  (27, 'Q'): 27,
  (27, 'R'): 27,
  (27, 'S'): 27,
  (27, 'T'): 27,
  (27, 'U'): 27,
  (27, 'V'): 27,
  (27, 'W'): 27,
  (27, 'X'): 27,
  (27, 'Y'): 27,
  (27, 'Z'): 27,
  (27, '['): 27,
  (27, '\\'): 27,
  (27, ']'): 27,
  (27, '^'): 27,
  (27, '_'): 27,
  (27, '`'): 27,
  (27, 'a'): 27,
  (27, 'b'): 27,
  (27, 'c'): 27,
  (27, 'd'): 27,
  (27, 'e'): 27,
  (27, 'f'): 27,
  (27, 'g'): 27,
  (27, 'h'): 27,
  (27, 'i'): 27,
  (27, 'j'): 27,
  (27, 'k'): 27,
  (27, 'l'): 27,
  (27, 'm'): 27,
  (27, 'n'): 27,
  (27, 'o'): 27,
  (27, 'p'): 27,
  (27, 'q'): 27,
  (27, 'r'): 27,
  (27, 's'): 27,
  (27, 't'): 27,
  (27, 'u'): 27,
  (27, 'v'): 27,
  (27, 'w'): 27,
  (27, 'x'): 27,
  (27, 'y'): 27,
  (27, 'z'): 27,
  (27, '{'): 27,
  (27, '|'): 27,
  (27, '}'): 27,
  (27, '~'): 27,
  (27, '\x7f'): 27,
  (27, '\x80'): 27,
  (27, '\x81'): 27,
  (27, '\x82'): 27,
  (27, '\x83'): 27,
  (27, '\x84'): 27,
  (27, '\x85'): 27,
  (27, '\x86'): 27,
  (27, '\x87'): 27,
  (27, '\x88'): 27,
  (27, '\x89'): 27,
  (27, '\x8a'): 27,
  (27, '\x8b'): 27,
  (27, '\x8c'): 27,
  (27, '\x8d'): 27,
  (27, '\x8e'): 27,
  (27, '\x8f'): 27,
  (27, '\x90'): 27,
  (27, '\x91'): 27,
  (27, '\x92'): 27,
  (27, '\x93'): 27,
  (27, '\x94'): 27,
  (27, '\x95'): 27,
  (27, '\x96'): 27,
  (27, '\x97'): 27,
  (27, '\x98'): 27,
  (27, '\x99'): 27,
  (27, '\x9a'): 27,
  (27, '\x9b'): 27,
  (27, '\x9c'): 27,
  (27, '\x9d'): 27,
  (27, '\x9e'): 27,
  (27, '\x9f'): 27,
  (27, '\xa0'): 27,
  (27, '\xa1'): 27,
  (27, '\xa2'): 27,
  (27, '\xa3'): 27,
  (27, '\xa4'): 27,
  (27, '\xa5'): 27,
  (27, '\xa6'): 27,
  (27, '\xa7'): 27,
  (27, '\xa8'): 27,
  (27, '\xa9'): 27,
  (27, '\xaa'): 27,
  (27, '\xab'): 27,
  (27, '\xac'): 27,
  (27, '\xad'): 27,
  (27, '\xae'): 27,
  (27, '\xaf'): 27,
  (27, '\xb0'): 27,
  (27, '\xb1'): 27,
  (27, '\xb2'): 27,
  (27, '\xb3'): 27,
  (27, '\xb4'): 27,
  (27, '\xb5'): 27,
  (27, '\xb6'): 27,
  (27, '\xb7'): 27,
  (27, '\xb8'): 27,
  (27, '\xb9'): 27,
  (27, '\xba'): 27,
  (27, '\xbb'): 27,
  (27, '\xbc'): 27,
  (27, '\xbd'): 27,
  (27, '\xbe'): 27,
  (27, '\xbf'): 27,
  (27, '\xc0'): 27,
  (27, '\xc1'): 27,
  (27, '\xc2'): 27,
  (27, '\xc3'): 27,
  (27, '\xc4'): 27,
  (27, '\xc5'): 27,
  (27, '\xc6'): 27,
  (27, '\xc7'): 27,
  (27, '\xc8'): 27,
  (27, '\xc9'): 27,
  (27, '\xca'): 27,
  (27, '\xcb'): 27,
  (27, '\xcc'): 27,
  (27, '\xcd'): 27,
  (27, '\xce'): 27,
  (27, '\xcf'): 27,
  (27, '\xd0'): 27,
  (27, '\xd1'): 27,
  (27, '\xd2'): 27,
  (27, '\xd3'): 27,
  (27, '\xd4'): 27,
  (27, '\xd5'): 27,
  (27, '\xd6'): 27,
  (27, '\xd7'): 27,
  (27, '\xd8'): 27,
  (27, '\xd9'): 27,
  (27, '\xda'): 27,
  (27, '\xdb'): 27,
  (27, '\xdc'): 27,
  (27, '\xdd'): 27,
  (27, '\xde'): 27,
  (27, '\xdf'): 27,
  (27, '\xe0'): 27,
  (27, '\xe1'): 27,
  (27, '\xe2'): 27,
  (27, '\xe3'): 27,
  (27, '\xe4'): 27,
  (27, '\xe5'): 27,
  (27, '\xe6'): 27,
  (27, '\xe7'): 27,
  (27, '\xe8'): 27,
  (27, '\xe9'): 27,
  (27, '\xea'): 27,
  (27, '\xeb'): 27,
  (27, '\xec'): 27,
  (27, '\xed'): 27,
  (27, '\xee'): 27,
  (27, '\xef'): 27,
  (27, '\xf0'): 27,
  (27, '\xf1'): 27,
  (27, '\xf2'): 27,
  (27, '\xf3'): 27,
  (27, '\xf4'): 27,
  (27, '\xf5'): 27,
  (27, '\xf6'): 27,
  (27, '\xf7'): 27,
  (27, '\xf8'): 27,
  (27, '\xf9'): 27,
  (27, '\xfa'): 27,
  (27, '\xfb'): 27,
  (27, '\xfc'): 27,
  (27, '\xfd'): 27,
  (27, '\xfe'): 27,
  (27, '\xff'): 27,
  (29, '-'): 47,
  (29, '>'): 48,
  (30, '.'): 39,
  (30, ':'): 40,
  (30, '<'): 38,
  (30, '='): 41,
  (30, '@'): 37,
  (30, '\\'): 42,
  (32, '0'): 10,
  (32, '1'): 10,
  (32, '2'): 10,
  (32, '3'): 10,
  (32, '4'): 10,
  (32, '5'): 10,
  (32, '6'): 10,
  (32, '7'): 10,
  (32, '8'): 10,
  (32, '9'): 10,
  (32, 'A'): 10,
  (32, 'B'): 10,
  (32, 'C'): 10,
  (32, 'D'): 10,
  (32, 'E'): 10,
  (32, 'F'): 10,
  (32, 'G'): 10,
  (32, 'H'): 10,
  (32, 'I'): 10,
  (32, 'J'): 10,
  (32, 'K'): 10,
  (32, 'L'): 10,
  (32, 'M'): 10,
  (32, 'N'): 10,
  (32, 'O'): 10,
  (32, 'P'): 10,
  (32, 'Q'): 10,
  (32, 'R'): 10,
  (32, 'S'): 10,
  (32, 'T'): 10,
  (32, 'U'): 10,
  (32, 'V'): 10,
  (32, 'W'): 10,
  (32, 'X'): 10,
  (32, 'Y'): 10,
  (32, 'Z'): 10,
  (32, '_'): 10,
  (32, 'a'): 10,
  (32, 'b'): 10,
  (32, 'c'): 10,
  (32, 'd'): 10,
  (32, 'e'): 10,
  (32, 'f'): 10,
  (32, 'g'): 10,
  (32, 'h'): 10,
  (32, 'i'): 10,
  (32, 'j'): 10,
  (32, 'k'): 10,
  (32, 'l'): 10,
  (32, 'm'): 10,
  (32, 'n'): 10,
  (32, 'o'): 10,
  (32, 'p'): 10,
  (32, 'q'): 10,
  (32, 'r'): 10,
  (32, 's'): 36,
  (32, 't'): 10,
  (32, 'u'): 10,
  (32, 'v'): 10,
  (32, 'w'): 10,
  (32, 'x'): 10,
  (32, 'y'): 10,
  (32, 'z'): 10,
  (33, '0'): 10,
  (33, '1'): 10,
  (33, '2'): 10,
  (33, '3'): 10,
  (33, '4'): 10,
  (33, '5'): 10,
  (33, '6'): 10,
  (33, '7'): 10,
  (33, '8'): 10,
  (33, '9'): 10,
  (33, 'A'): 10,
  (33, 'B'): 10,
  (33, 'C'): 10,
  (33, 'D'): 10,
  (33, 'E'): 10,
  (33, 'F'): 10,
  (33, 'G'): 10,
  (33, 'H'): 10,
  (33, 'I'): 10,
  (33, 'J'): 10,
  (33, 'K'): 10,
  (33, 'L'): 10,
  (33, 'M'): 10,
  (33, 'N'): 10,
  (33, 'O'): 10,
  (33, 'P'): 10,
  (33, 'Q'): 10,
  (33, 'R'): 10,
  (33, 'S'): 10,
  (33, 'T'): 10,
  (33, 'U'): 10,
  (33, 'V'): 10,
  (33, 'W'): 10,
  (33, 'X'): 10,
  (33, 'Y'): 10,
  (33, 'Z'): 10,
  (33, '_'): 10,
  (33, 'a'): 10,
  (33, 'b'): 10,
  (33, 'c'): 10,
  (33, 'd'): 10,
  (33, 'e'): 10,
  (33, 'f'): 10,
  (33, 'g'): 10,
  (33, 'h'): 10,
  (33, 'i'): 10,
  (33, 'j'): 10,
  (33, 'k'): 10,
  (33, 'l'): 10,
  (33, 'm'): 10,
  (33, 'n'): 10,
  (33, 'o'): 34,
  (33, 'p'): 10,
  (33, 'q'): 10,
  (33, 'r'): 10,
  (33, 's'): 10,
  (33, 't'): 10,
  (33, 'u'): 10,
  (33, 'v'): 10,
  (33, 'w'): 10,
  (33, 'x'): 10,
  (33, 'y'): 10,
  (33, 'z'): 10,
  (34, '0'): 10,
  (34, '1'): 10,
  (34, '2'): 10,
  (34, '3'): 10,
  (34, '4'): 10,
  (34, '5'): 10,
  (34, '6'): 10,
  (34, '7'): 10,
  (34, '8'): 10,
  (34, '9'): 10,
  (34, 'A'): 10,
  (34, 'B'): 10,
  (34, 'C'): 10,
  (34, 'D'): 10,
  (34, 'E'): 10,
  (34, 'F'): 10,
  (34, 'G'): 10,
  (34, 'H'): 10,
  (34, 'I'): 10,
  (34, 'J'): 10,
  (34, 'K'): 10,
  (34, 'L'): 10,
  (34, 'M'): 10,
  (34, 'N'): 10,
  (34, 'O'): 10,
  (34, 'P'): 10,
  (34, 'Q'): 10,
  (34, 'R'): 10,
  (34, 'S'): 10,
  (34, 'T'): 10,
  (34, 'U'): 10,
  (34, 'V'): 10,
  (34, 'W'): 10,
  (34, 'X'): 10,
  (34, 'Y'): 10,
  (34, 'Z'): 10,
  (34, '_'): 10,
  (34, 'a'): 10,
  (34, 'b'): 10,
  (34, 'c'): 10,
  (34, 'd'): 35,
  (34, 'e'): 10,
  (34, 'f'): 10,
  (34, 'g'): 10,
  (34, 'h'): 10,
  (34, 'i'): 10,
  (34, 'j'): 10,
  (34, 'k'): 10,
  (34, 'l'): 10,
  (34, 'm'): 10,
  (34, 'n'): 10,
  (34, 'o'): 10,
  (34, 'p'): 10,
  (34, 'q'): 10,
  (34, 'r'): 10,
  (34, 's'): 10,
  (34, 't'): 10,
  (34, 'u'): 10,
  (34, 'v'): 10,
  (34, 'w'): 10,
  (34, 'x'): 10,
  (34, 'y'): 10,
  (34, 'z'): 10,
  (35, '0'): 10,
  (35, '1'): 10,
  (35, '2'): 10,
  (35, '3'): 10,
  (35, '4'): 10,
  (35, '5'): 10,
  (35, '6'): 10,
  (35, '7'): 10,
  (35, '8'): 10,
  (35, '9'): 10,
  (35, 'A'): 10,
  (35, 'B'): 10,
  (35, 'C'): 10,
  (35, 'D'): 10,
  (35, 'E'): 10,
  (35, 'F'): 10,
  (35, 'G'): 10,
  (35, 'H'): 10,
  (35, 'I'): 10,
  (35, 'J'): 10,
  (35, 'K'): 10,
  (35, 'L'): 10,
  (35, 'M'): 10,
  (35, 'N'): 10,
  (35, 'O'): 10,
  (35, 'P'): 10,
  (35, 'Q'): 10,
  (35, 'R'): 10,
  (35, 'S'): 10,
  (35, 'T'): 10,
  (35, 'U'): 10,
  (35, 'V'): 10,
  (35, 'W'): 10,
  (35, 'X'): 10,
  (35, 'Y'): 10,
  (35, 'Z'): 10,
  (35, '_'): 10,
  (35, 'a'): 10,
  (35, 'b'): 10,
  (35, 'c'): 10,
  (35, 'd'): 10,
  (35, 'e'): 10,
  (35, 'f'): 10,
  (35, 'g'): 10,
  (35, 'h'): 10,
  (35, 'i'): 10,
  (35, 'j'): 10,
  (35, 'k'): 10,
  (35, 'l'): 10,
  (35, 'm'): 10,
  (35, 'n'): 10,
  (35, 'o'): 10,
  (35, 'p'): 10,
  (35, 'q'): 10,
  (35, 'r'): 10,
  (35, 's'): 10,
  (35, 't'): 10,
  (35, 'u'): 10,
  (35, 'v'): 10,
  (35, 'w'): 10,
  (35, 'x'): 10,
  (35, 'y'): 10,
  (35, 'z'): 10,
  (36, '0'): 10,
  (36, '1'): 10,
  (36, '2'): 10,
  (36, '3'): 10,
  (36, '4'): 10,
  (36, '5'): 10,
  (36, '6'): 10,
  (36, '7'): 10,
  (36, '8'): 10,
  (36, '9'): 10,
  (36, 'A'): 10,
  (36, 'B'): 10,
  (36, 'C'): 10,
  (36, 'D'): 10,
  (36, 'E'): 10,
  (36, 'F'): 10,
  (36, 'G'): 10,
  (36, 'H'): 10,
  (36, 'I'): 10,
  (36, 'J'): 10,
  (36, 'K'): 10,
  (36, 'L'): 10,
  (36, 'M'): 10,
  (36, 'N'): 10,
  (36, 'O'): 10,
  (36, 'P'): 10,
  (36, 'Q'): 10,
  (36, 'R'): 10,
  (36, 'S'): 10,
  (36, 'T'): 10,
  (36, 'U'): 10,
  (36, 'V'): 10,
  (36, 'W'): 10,
  (36, 'X'): 10,
  (36, 'Y'): 10,
  (36, 'Z'): 10,
  (36, '_'): 10,
  (36, 'a'): 10,
  (36, 'b'): 10,
  (36, 'c'): 10,
  (36, 'd'): 10,
  (36, 'e'): 10,
  (36, 'f'): 10,
  (36, 'g'): 10,
  (36, 'h'): 10,
  (36, 'i'): 10,
  (36, 'j'): 10,
  (36, 'k'): 10,
  (36, 'l'): 10,
  (36, 'm'): 10,
  (36, 'n'): 10,
  (36, 'o'): 10,
  (36, 'p'): 10,
  (36, 'q'): 10,
  (36, 'r'): 10,
  (36, 's'): 10,
  (36, 't'): 10,
  (36, 'u'): 10,
  (36, 'v'): 10,
  (36, 'w'): 10,
  (36, 'x'): 10,
  (36, 'y'): 10,
  (36, 'z'): 10,
  (37, '='): 46,
  (39, '.'): 45,
  (40, '='): 44,
  (42, '='): 43,
  (47, '>'): 49,
  (50, '0'): 10,
  (50, '1'): 10,
  (50, '2'): 10,
  (50, '3'): 10,
  (50, '4'): 10,
  (50, '5'): 10,
  (50, '6'): 10,
  (50, '7'): 10,
  (50, '8'): 10,
  (50, '9'): 10,
  (50, 'A'): 10,
  (50, 'B'): 10,
  (50, 'C'): 10,
  (50, 'D'): 10,
  (50, 'E'): 10,
  (50, 'F'): 10,
  (50, 'G'): 10,
  (50, 'H'): 10,
  (50, 'I'): 10,
  (50, 'J'): 10,
  (50, 'K'): 10,
  (50, 'L'): 10,
  (50, 'M'): 10,
  (50, 'N'): 10,
  (50, 'O'): 10,
  (50, 'P'): 10,
  (50, 'Q'): 10,
  (50, 'R'): 10,
  (50, 'S'): 10,
  (50, 'T'): 10,
  (50, 'U'): 10,
  (50, 'V'): 10,
  (50, 'W'): 10,
  (50, 'X'): 10,
  (50, 'Y'): 10,
  (50, 'Z'): 10,
  (50, '_'): 10,
  (50, 'a'): 10,
  (50, 'b'): 10,
  (50, 'c'): 10,
  (50, 'd'): 10,
  (50, 'e'): 10,
  (50, 'f'): 10,
  (50, 'g'): 10,
  (50, 'h'): 10,
  (50, 'i'): 10,
  (50, 'j'): 10,
  (50, 'k'): 10,
  (50, 'l'): 10,
  (50, 'm'): 51,
  (50, 'n'): 10,
  (50, 'o'): 10,
  (50, 'p'): 10,
  (50, 'q'): 10,
  (50, 'r'): 10,
  (50, 's'): 10,
  (50, 't'): 10,
  (50, 'u'): 10,
  (50, 'v'): 10,
  (50, 'w'): 10,
  (50, 'x'): 10,
  (50, 'y'): 10,
  (50, 'z'): 10,
  (51, '0'): 10,
  (51, '1'): 10,
  (51, '2'): 10,
  (51, '3'): 10,
  (51, '4'): 10,
  (51, '5'): 10,
  (51, '6'): 10,
  (51, '7'): 10,
  (51, '8'): 10,
  (51, '9'): 10,
  (51, 'A'): 10,
  (51, 'B'): 10,
  (51, 'C'): 10,
  (51, 'D'): 10,
  (51, 'E'): 10,
  (51, 'F'): 10,
  (51, 'G'): 10,
  (51, 'H'): 10,
  (51, 'I'): 10,
  (51, 'J'): 10,
  (51, 'K'): 10,
  (51, 'L'): 10,
  (51, 'M'): 10,
  (51, 'N'): 10,
  (51, 'O'): 10,
  (51, 'P'): 10,
  (51, 'Q'): 10,
  (51, 'R'): 10,
  (51, 'S'): 10,
  (51, 'T'): 10,
  (51, 'U'): 10,
  (51, 'V'): 10,
  (51, 'W'): 10,
  (51, 'X'): 10,
  (51, 'Y'): 10,
  (51, 'Z'): 10,
  (51, '_'): 10,
  (51, 'a'): 10,
  (51, 'b'): 10,
  (51, 'c'): 10,
  (51, 'd'): 10,
  (51, 'e'): 10,
  (51, 'f'): 10,
  (51, 'g'): 10,
  (51, 'h'): 10,
  (51, 'i'): 10,
  (51, 'j'): 10,
  (51, 'k'): 10,
  (51, 'l'): 10,
  (51, 'm'): 10,
  (51, 'n'): 10,
  (51, 'o'): 10,
  (51, 'p'): 10,
  (51, 'q'): 10,
  (51, 'r'): 10,
  (51, 's'): 10,
  (51, 't'): 10,
  (51, 'u'): 10,
  (51, 'v'): 10,
  (51, 'w'): 10,
  (51, 'x'): 10,
  (51, 'y'): 10,
  (51, 'z'): 10,
  (57, '\x00'): 57,
  (57, '\x01'): 57,
  (57, '\x02'): 57,
  (57, '\x03'): 57,
  (57, '\x04'): 57,
  (57, '\x05'): 57,
  (57, '\x06'): 57,
  (57, '\x07'): 57,
  (57, '\x08'): 57,
  (57, '\t'): 57,
  (57, '\n'): 57,
  (57, '\x0b'): 57,
  (57, '\x0c'): 57,
  (57, '\r'): 57,
  (57, '\x0e'): 57,
  (57, '\x0f'): 57,
  (57, '\x10'): 57,
  (57, '\x11'): 57,
  (57, '\x12'): 57,
  (57, '\x13'): 57,
  (57, '\x14'): 57,
  (57, '\x15'): 57,
  (57, '\x16'): 57,
  (57, '\x17'): 57,
  (57, '\x18'): 57,
  (57, '\x19'): 57,
  (57, '\x1a'): 57,
  (57, '\x1b'): 57,
  (57, '\x1c'): 57,
  (57, '\x1d'): 57,
  (57, '\x1e'): 57,
  (57, '\x1f'): 57,
  (57, ' '): 57,
  (57, '!'): 57,
  (57, '"'): 57,
  (57, '#'): 57,
  (57, '$'): 57,
  (57, '%'): 57,
  (57, '&'): 57,
  (57, "'"): 57,
  (57, '('): 57,
  (57, ')'): 57,
  (57, '*'): 60,
  (57, '+'): 57,
  (57, ','): 57,
  (57, '-'): 57,
  (57, '.'): 57,
  (57, '/'): 57,
  (57, '0'): 57,
  (57, '1'): 57,
  (57, '2'): 57,
  (57, '3'): 57,
  (57, '4'): 57,
  (57, '5'): 57,
  (57, '6'): 57,
  (57, '7'): 57,
  (57, '8'): 57,
  (57, '9'): 57,
  (57, ':'): 57,
  (57, ';'): 57,
  (57, '<'): 57,
  (57, '='): 57,
  (57, '>'): 57,
  (57, '?'): 57,
  (57, '@'): 57,
  (57, 'A'): 57,
  (57, 'B'): 57,
  (57, 'C'): 57,
  (57, 'D'): 57,
  (57, 'E'): 57,
  (57, 'F'): 57,
  (57, 'G'): 57,
  (57, 'H'): 57,
  (57, 'I'): 57,
  (57, 'J'): 57,
  (57, 'K'): 57,
  (57, 'L'): 57,
  (57, 'M'): 57,
  (57, 'N'): 57,
  (57, 'O'): 57,
  (57, 'P'): 57,
  (57, 'Q'): 57,
  (57, 'R'): 57,
  (57, 'S'): 57,
  (57, 'T'): 57,
  (57, 'U'): 57,
  (57, 'V'): 57,
  (57, 'W'): 57,
  (57, 'X'): 57,
  (57, 'Y'): 57,
  (57, 'Z'): 57,
  (57, '['): 57,
  (57, '\\'): 57,
  (57, ']'): 57,
  (57, '^'): 57,
  (57, '_'): 57,
  (57, '`'): 57,
  (57, 'a'): 57,
  (57, 'b'): 57,
  (57, 'c'): 57,
  (57, 'd'): 57,
  (57, 'e'): 57,
  (57, 'f'): 57,
  (57, 'g'): 57,
  (57, 'h'): 57,
  (57, 'i'): 57,
  (57, 'j'): 57,
  (57, 'k'): 57,
  (57, 'l'): 57,
  (57, 'm'): 57,
  (57, 'n'): 57,
  (57, 'o'): 57,
  (57, 'p'): 57,
  (57, 'q'): 57,
  (57, 'r'): 57,
  (57, 's'): 57,
  (57, 't'): 57,
  (57, 'u'): 57,
  (57, 'v'): 57,
  (57, 'w'): 57,
  (57, 'x'): 57,
  (57, 'y'): 57,
  (57, 'z'): 57,
  (57, '{'): 57,
  (57, '|'): 57,
  (57, '}'): 57,
  (57, '~'): 57,
  (57, '\x7f'): 57,
  (57, '\x80'): 57,
  (57, '\x81'): 57,
  (57, '\x82'): 57,
  (57, '\x83'): 57,
  (57, '\x84'): 57,
  (57, '\x85'): 57,
  (57, '\x86'): 57,
  (57, '\x87'): 57,
  (57, '\x88'): 57,
  (57, '\x89'): 57,
  (57, '\x8a'): 57,
  (57, '\x8b'): 57,
  (57, '\x8c'): 57,
  (57, '\x8d'): 57,
  (57, '\x8e'): 57,
  (57, '\x8f'): 57,
  (57, '\x90'): 57,
  (57, '\x91'): 57,
  (57, '\x92'): 57,
  (57, '\x93'): 57,
  (57, '\x94'): 57,
  (57, '\x95'): 57,
  (57, '\x96'): 57,
  (57, '\x97'): 57,
  (57, '\x98'): 57,
  (57, '\x99'): 57,
  (57, '\x9a'): 57,
  (57, '\x9b'): 57,
  (57, '\x9c'): 57,
  (57, '\x9d'): 57,
  (57, '\x9e'): 57,
  (57, '\x9f'): 57,
  (57, '\xa0'): 57,
  (57, '\xa1'): 57,
  (57, '\xa2'): 57,
  (57, '\xa3'): 57,
  (57, '\xa4'): 57,
  (57, '\xa5'): 57,
  (57, '\xa6'): 57,
  (57, '\xa7'): 57,
  (57, '\xa8'): 57,
  (57, '\xa9'): 57,
  (57, '\xaa'): 57,
  (57, '\xab'): 57,
  (57, '\xac'): 57,
  (57, '\xad'): 57,
  (57, '\xae'): 57,
  (57, '\xaf'): 57,
  (57, '\xb0'): 57,
  (57, '\xb1'): 57,
  (57, '\xb2'): 57,
  (57, '\xb3'): 57,
  (57, '\xb4'): 57,
  (57, '\xb5'): 57,
  (57, '\xb6'): 57,
  (57, '\xb7'): 57,
  (57, '\xb8'): 57,
  (57, '\xb9'): 57,
  (57, '\xba'): 57,
  (57, '\xbb'): 57,
  (57, '\xbc'): 57,
  (57, '\xbd'): 57,
  (57, '\xbe'): 57,
  (57, '\xbf'): 57,
  (57, '\xc0'): 57,
  (57, '\xc1'): 57,
  (57, '\xc2'): 57,
  (57, '\xc3'): 57,
  (57, '\xc4'): 57,
  (57, '\xc5'): 57,
  (57, '\xc6'): 57,
  (57, '\xc7'): 57,
  (57, '\xc8'): 57,
  (57, '\xc9'): 57,
  (57, '\xca'): 57,
  (57, '\xcb'): 57,
  (57, '\xcc'): 57,
  (57, '\xcd'): 57,
  (57, '\xce'): 57,
  (57, '\xcf'): 57,
  (57, '\xd0'): 57,
  (57, '\xd1'): 57,
  (57, '\xd2'): 57,
  (57, '\xd3'): 57,
  (57, '\xd4'): 57,
  (57, '\xd5'): 57,
  (57, '\xd6'): 57,
  (57, '\xd7'): 57,
  (57, '\xd8'): 57,
  (57, '\xd9'): 57,
  (57, '\xda'): 57,
  (57, '\xdb'): 57,
  (57, '\xdc'): 57,
  (57, '\xdd'): 57,
  (57, '\xde'): 57,
  (57, '\xdf'): 57,
  (57, '\xe0'): 57,
  (57, '\xe1'): 57,
  (57, '\xe2'): 57,
  (57, '\xe3'): 57,
  (57, '\xe4'): 57,
  (57, '\xe5'): 57,
  (57, '\xe6'): 57,
  (57, '\xe7'): 57,
  (57, '\xe8'): 57,
  (57, '\xe9'): 57,
  (57, '\xea'): 57,
  (57, '\xeb'): 57,
  (57, '\xec'): 57,
  (57, '\xed'): 57,
  (57, '\xee'): 57,
  (57, '\xef'): 57,
  (57, '\xf0'): 57,
  (57, '\xf1'): 57,
  (57, '\xf2'): 57,
  (57, '\xf3'): 57,
  (57, '\xf4'): 57,
  (57, '\xf5'): 57,
  (57, '\xf6'): 57,
  (57, '\xf7'): 57,
  (57, '\xf8'): 57,
  (57, '\xf9'): 57,
  (57, '\xfa'): 57,
  (57, '\xfb'): 57,
  (57, '\xfc'): 57,
  (57, '\xfd'): 57,
  (57, '\xfe'): 57,
  (57, '\xff'): 57,
  (60, '\x00'): 57,
  (60, '\x01'): 57,
  (60, '\x02'): 57,
  (60, '\x03'): 57,
  (60, '\x04'): 57,
  (60, '\x05'): 57,
  (60, '\x06'): 57,
  (60, '\x07'): 57,
  (60, '\x08'): 57,
  (60, '\t'): 57,
  (60, '\n'): 57,
  (60, '\x0b'): 57,
  (60, '\x0c'): 57,
  (60, '\r'): 57,
  (60, '\x0e'): 57,
  (60, '\x0f'): 57,
  (60, '\x10'): 57,
  (60, '\x11'): 57,
  (60, '\x12'): 57,
  (60, '\x13'): 57,
  (60, '\x14'): 57,
  (60, '\x15'): 57,
  (60, '\x16'): 57,
  (60, '\x17'): 57,
  (60, '\x18'): 57,
  (60, '\x19'): 57,
  (60, '\x1a'): 57,
  (60, '\x1b'): 57,
  (60, '\x1c'): 57,
  (60, '\x1d'): 57,
  (60, '\x1e'): 57,
  (60, '\x1f'): 57,
  (60, ' '): 57,
  (60, '!'): 57,
  (60, '"'): 57,
  (60, '#'): 57,
  (60, '$'): 57,
  (60, '%'): 57,
  (60, '&'): 57,
  (60, "'"): 57,
  (60, '('): 57,
  (60, ')'): 57,
  (60, '*'): 57,
  (60, '+'): 57,
  (60, ','): 57,
  (60, '-'): 57,
  (60, '.'): 57,
  (60, '/'): 1,
  (60, '0'): 57,
  (60, '1'): 57,
  (60, '2'): 57,
  (60, '3'): 57,
  (60, '4'): 57,
  (60, '5'): 57,
  (60, '6'): 57,
  (60, '7'): 57,
  (60, '8'): 57,
  (60, '9'): 57,
  (60, ':'): 57,
  (60, ';'): 57,
  (60, '<'): 57,
  (60, '='): 57,
  (60, '>'): 57,
  (60, '?'): 57,
  (60, '@'): 57,
  (60, 'A'): 57,
  (60, 'B'): 57,
  (60, 'C'): 57,
  (60, 'D'): 57,
  (60, 'E'): 57,
  (60, 'F'): 57,
  (60, 'G'): 57,
  (60, 'H'): 57,
  (60, 'I'): 57,
  (60, 'J'): 57,
  (60, 'K'): 57,
  (60, 'L'): 57,
  (60, 'M'): 57,
  (60, 'N'): 57,
  (60, 'O'): 57,
  (60, 'P'): 57,
  (60, 'Q'): 57,
  (60, 'R'): 57,
  (60, 'S'): 57,
  (60, 'T'): 57,
  (60, 'U'): 57,
  (60, 'V'): 57,
  (60, 'W'): 57,
  (60, 'X'): 57,
  (60, 'Y'): 57,
  (60, 'Z'): 57,
  (60, '['): 57,
  (60, '\\'): 57,
  (60, ']'): 57,
  (60, '^'): 57,
  (60, '_'): 57,
  (60, '`'): 57,
  (60, 'a'): 57,
  (60, 'b'): 57,
  (60, 'c'): 57,
  (60, 'd'): 57,
  (60, 'e'): 57,
  (60, 'f'): 57,
  (60, 'g'): 57,
  (60, 'h'): 57,
  (60, 'i'): 57,
  (60, 'j'): 57,
  (60, 'k'): 57,
  (60, 'l'): 57,
  (60, 'm'): 57,
  (60, 'n'): 57,
  (60, 'o'): 57,
  (60, 'p'): 57,
  (60, 'q'): 57,
  (60, 'r'): 57,
  (60, 's'): 57,
  (60, 't'): 57,
  (60, 'u'): 57,
  (60, 'v'): 57,
  (60, 'w'): 57,
  (60, 'x'): 57,
  (60, 'y'): 57,
  (60, 'z'): 57,
  (60, '{'): 57,
  (60, '|'): 57,
  (60, '}'): 57,
  (60, '~'): 57,
  (60, '\x7f'): 57,
  (60, '\x80'): 57,
  (60, '\x81'): 57,
  (60, '\x82'): 57,
  (60, '\x83'): 57,
  (60, '\x84'): 57,
  (60, '\x85'): 57,
  (60, '\x86'): 57,
  (60, '\x87'): 57,
  (60, '\x88'): 57,
  (60, '\x89'): 57,
  (60, '\x8a'): 57,
  (60, '\x8b'): 57,
  (60, '\x8c'): 57,
  (60, '\x8d'): 57,
  (60, '\x8e'): 57,
  (60, '\x8f'): 57,
  (60, '\x90'): 57,
  (60, '\x91'): 57,
  (60, '\x92'): 57,
  (60, '\x93'): 57,
  (60, '\x94'): 57,
  (60, '\x95'): 57,
  (60, '\x96'): 57,
  (60, '\x97'): 57,
  (60, '\x98'): 57,
  (60, '\x99'): 57,
  (60, '\x9a'): 57,
  (60, '\x9b'): 57,
  (60, '\x9c'): 57,
  (60, '\x9d'): 57,
  (60, '\x9e'): 57,
  (60, '\x9f'): 57,
  (60, '\xa0'): 57,
  (60, '\xa1'): 57,
  (60, '\xa2'): 57,
  (60, '\xa3'): 57,
  (60, '\xa4'): 57,
  (60, '\xa5'): 57,
  (60, '\xa6'): 57,
  (60, '\xa7'): 57,
  (60, '\xa8'): 57,
  (60, '\xa9'): 57,
  (60, '\xaa'): 57,
  (60, '\xab'): 57,
  (60, '\xac'): 57,
  (60, '\xad'): 57,
  (60, '\xae'): 57,
  (60, '\xaf'): 57,
  (60, '\xb0'): 57,
  (60, '\xb1'): 57,
  (60, '\xb2'): 57,
  (60, '\xb3'): 57,
  (60, '\xb4'): 57,
  (60, '\xb5'): 57,
  (60, '\xb6'): 57,
  (60, '\xb7'): 57,
  (60, '\xb8'): 57,
  (60, '\xb9'): 57,
  (60, '\xba'): 57,
  (60, '\xbb'): 57,
  (60, '\xbc'): 57,
  (60, '\xbd'): 57,
  (60, '\xbe'): 57,
  (60, '\xbf'): 57,
  (60, '\xc0'): 57,
  (60, '\xc1'): 57,
  (60, '\xc2'): 57,
  (60, '\xc3'): 57,
  (60, '\xc4'): 57,
  (60, '\xc5'): 57,
  (60, '\xc6'): 57,
  (60, '\xc7'): 57,
  (60, '\xc8'): 57,
  (60, '\xc9'): 57,
  (60, '\xca'): 57,
  (60, '\xcb'): 57,
  (60, '\xcc'): 57,
  (60, '\xcd'): 57,
  (60, '\xce'): 57,
  (60, '\xcf'): 57,
  (60, '\xd0'): 57,
  (60, '\xd1'): 57,
  (60, '\xd2'): 57,
  (60, '\xd3'): 57,
  (60, '\xd4'): 57,
  (60, '\xd5'): 57,
  (60, '\xd6'): 57,
  (60, '\xd7'): 57,
  (60, '\xd8'): 57,
  (60, '\xd9'): 57,
  (60, '\xda'): 57,
  (60, '\xdb'): 57,
  (60, '\xdc'): 57,
  (60, '\xdd'): 57,
  (60, '\xde'): 57,
  (60, '\xdf'): 57,
  (60, '\xe0'): 57,
  (60, '\xe1'): 57,
  (60, '\xe2'): 57,
  (60, '\xe3'): 57,
  (60, '\xe4'): 57,
  (60, '\xe5'): 57,
  (60, '\xe6'): 57,
  (60, '\xe7'): 57,
  (60, '\xe8'): 57,
  (60, '\xe9'): 57,
  (60, '\xea'): 57,
  (60, '\xeb'): 57,
  (60, '\xec'): 57,
  (60, '\xed'): 57,
  (60, '\xee'): 57,
  (60, '\xef'): 57,
  (60, '\xf0'): 57,
  (60, '\xf1'): 57,
  (60, '\xf2'): 57,
  (60, '\xf3'): 57,
  (60, '\xf4'): 57,
  (60, '\xf5'): 57,
  (60, '\xf6'): 57,
  (60, '\xf7'): 57,
  (60, '\xf8'): 57,
  (60, '\xf9'): 57,
  (60, '\xfa'): 57,
  (60, '\xfb'): 57,
  (60, '\xfc'): 57,
  (60, '\xfd'): 57,
  (60, '\xfe'): 57,
  (60, '\xff'): 57,
  (61, '0'): 10,
  (61, '1'): 10,
  (61, '2'): 10,
  (61, '3'): 10,
  (61, '4'): 10,
  (61, '5'): 10,
  (61, '6'): 10,
  (61, '7'): 10,
  (61, '8'): 10,
  (61, '9'): 10,
  (61, 'A'): 10,
  (61, 'B'): 10,
  (61, 'C'): 10,
  (61, 'D'): 10,
  (61, 'E'): 10,
  (61, 'F'): 10,
  (61, 'G'): 10,
  (61, 'H'): 10,
  (61, 'I'): 10,
  (61, 'J'): 10,
  (61, 'K'): 10,
  (61, 'L'): 10,
  (61, 'M'): 10,
  (61, 'N'): 10,
  (61, 'O'): 10,
  (61, 'P'): 10,
  (61, 'Q'): 10,
  (61, 'R'): 10,
  (61, 'S'): 10,
  (61, 'T'): 10,
  (61, 'U'): 10,
  (61, 'V'): 10,
  (61, 'W'): 10,
  (61, 'X'): 10,
  (61, 'Y'): 10,
  (61, 'Z'): 10,
  (61, '_'): 10,
  (61, 'a'): 10,
  (61, 'b'): 10,
  (61, 'c'): 10,
  (61, 'd'): 10,
  (61, 'e'): 10,
  (61, 'f'): 10,
  (61, 'g'): 10,
  (61, 'h'): 10,
  (61, 'i'): 10,
  (61, 'j'): 10,
  (61, 'k'): 10,
  (61, 'l'): 10,
  (61, 'm'): 10,
  (61, 'n'): 10,
  (61, 'o'): 10,
  (61, 'p'): 10,
  (61, 'q'): 10,
  (61, 'r'): 62,
  (61, 's'): 10,
  (61, 't'): 10,
  (61, 'u'): 10,
  (61, 'v'): 10,
  (61, 'w'): 10,
  (61, 'x'): 10,
  (61, 'y'): 10,
  (61, 'z'): 10,
  (62, '0'): 10,
  (62, '1'): 10,
  (62, '2'): 10,
  (62, '3'): 10,
  (62, '4'): 10,
  (62, '5'): 10,
  (62, '6'): 10,
  (62, '7'): 10,
  (62, '8'): 10,
  (62, '9'): 10,
  (62, 'A'): 10,
  (62, 'B'): 10,
  (62, 'C'): 10,
  (62, 'D'): 10,
  (62, 'E'): 10,
  (62, 'F'): 10,
  (62, 'G'): 10,
  (62, 'H'): 10,
  (62, 'I'): 10,
  (62, 'J'): 10,
  (62, 'K'): 10,
  (62, 'L'): 10,
  (62, 'M'): 10,
  (62, 'N'): 10,
  (62, 'O'): 10,
  (62, 'P'): 10,
  (62, 'Q'): 10,
  (62, 'R'): 10,
  (62, 'S'): 10,
  (62, 'T'): 10,
  (62, 'U'): 10,
  (62, 'V'): 10,
  (62, 'W'): 10,
  (62, 'X'): 10,
  (62, 'Y'): 10,
  (62, 'Z'): 10,
  (62, '_'): 10,
  (62, 'a'): 10,
  (62, 'b'): 10,
  (62, 'c'): 10,
  (62, 'd'): 10,
  (62, 'e'): 10,
  (62, 'f'): 10,
  (62, 'g'): 10,
  (62, 'h'): 10,
  (62, 'i'): 10,
  (62, 'j'): 10,
  (62, 'k'): 10,
  (62, 'l'): 10,
  (62, 'm'): 10,
  (62, 'n'): 10,
  (62, 'o'): 10,
  (62, 'p'): 10,
  (62, 'q'): 10,
  (62, 'r'): 10,
  (62, 's'): 10,
  (62, 't'): 10,
  (62, 'u'): 10,
  (62, 'v'): 10,
  (62, 'w'): 10,
  (62, 'x'): 10,
  (62, 'y'): 10,
  (62, 'z'): 10,
  (64, '='): 66,
  (67, '<'): 71,
  (69, '='): 70,
  (73, '0'): 74,
  (73, '1'): 74,
  (73, '2'): 74,
  (73, '3'): 74,
  (73, '4'): 74,
  (73, '5'): 74,
  (73, '6'): 74,
  (73, '7'): 74,
  (73, '8'): 74,
  (73, '9'): 74,
  (74, '0'): 74,
  (74, '1'): 74,
  (74, '2'): 74,
  (74, '3'): 74,
  (74, '4'): 74,
  (74, '5'): 74,
  (74, '6'): 74,
  (74, '7'): 74,
  (74, '8'): 74,
  (74, '9'): 74},
 set([1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 38, 41, 43, 44, 45, 46, 48, 49, 50, 51, 52, 53, 54, 55, 56, 58, 59, 61, 62, 63, 64, 65, 66, 68, 69, 70, 71, 72, 74]),
 set([1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 38, 41, 43, 44, 45, 46, 48, 49, 50, 51, 52, 53, 54, 55, 56, 58, 59, 61, 62, 63, 64, 65, 66, 68, 69, 70, 71, 72, 74]),
 ['0, start|, 0, start|, 0, 0, 0, 0, 0, start|, 0, 0, 0, start|, 0, start|, 0, start|, 0, 0, 0, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0',
  'IGNORE',
  '(',
  'ATOM',
  'NUMBER',
  'NUMBER',
  'ATOM',
  '1, 1, 1, 1',
  'VAR',
  'ATOM',
  'ATOM',
  'ATOM',
  '|',
  '0, 1, 0, start|, 0, final*, start*, 0, 0, 1, final|, start|, 0, final*, start*, 0, 0, final|, start|, 0, 1, final*, start*',
  'ATOM',
  'ATOM',
  'ATOM',
  'ATOM',
  '[',
  'ATOM',
  '.',
  'ATOM',
  'ATOM',
  'ATOM',
  'ATOM',
  'ATOM',
  'ATOM',
  'IGNORE',
  ')',
  'ATOM',
  'ATOM',
  ']',
  'ATOM',
  'ATOM',
  'ATOM',
  'ATOM',
  'ATOM',
  '2',
  'ATOM',
  '2',
  '2',
  'ATOM',
  '2',
  'ATOM',
  'ATOM',
  'ATOM',
  'ATOM',
  '2',
  'ATOM',
  'ATOM',
  'ATOM',
  'ATOM',
  'ATOM',
  'ATOM',
  'ATOM',
  'ATOM',
  'ATOM',
  'final*, start*, 1, 0, 0, start|, 0, final*, start*, 0, final*, start*, 0, 0, 1, final|, start|, 0, final*, start*, 0, final*, start*, 0, 0, final|, start|, 0, 1, final*, start*, 0, final*, 0, start|, 0, final*, start*, final*, start*, 0, 0, final*, 1, final|, final*, 0, start|, 0, final*, start*, final*, start*, 0, 0, final*, final|, 1, final*, 0, 1, final|, start|, 0, final*, start*, final*, start*, 0, 0, final*, final*, 0, final|, start|, 0, 1, final*, start*, final*, start*, 0, 0, final*',
  'ATOM',
  'ATOM',
  '1, 0, 1, 0, start|',
  'ATOM',
  'ATOM',
  'ATOM',
  'ATOM',
  'ATOM',
  'ATOM',
  '2',
  'ATOM',
  'ATOM',
  'ATOM',
  'ATOM',
  'ATOM',
  '1, 0',
  'NUMBER']), {'IGNORE': None})
basic_rules = [Rule('query', [['toplevel_op_expr', '.', 'EOF']]), Rule('fact', [['toplevel_op_expr', '.']]), Rule('complexterm', [['ATOM', '(', 'toplevel_op_expr', ')'], ['expr']]), Rule('expr', [['VAR'], ['NUMBER'], ['+', 'NUMBER'], ['-', 'NUMBER'], ['ATOM'], ['(', 'toplevel_op_expr', ')'], ['listexpr']]), Rule('listexpr', [['[', 'listbody', ']']]), Rule('listbody', [['toplevel_op_expr', '|', 'toplevel_op_expr'], ['toplevel_op_expr']])]
# generated code between this line and its other occurence
 
if __name__ == '__main__':
    f = py.magic.autopath()
    oldcontent = f.read()
    s = "# GENERATED CODE BETWEEN THIS LINE AND ITS OTHER OCCURENCE\n".lower()
    pre, gen, after = oldcontent.split(s)

    lexer, parser_fact, parser_query, basic_rules = make_all()
    newcontent = ("%s%s\nparser_fact = %r\nparser_query = %r\n%s\n"
                  "basic_rules = %r\n%s%s") % (
            pre, s, parser_fact, parser_query, lexer.get_dummy_repr(),
            basic_rules, s, after)
    print newcontent
    f.write(newcontent)

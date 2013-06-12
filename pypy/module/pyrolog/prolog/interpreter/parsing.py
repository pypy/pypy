import py
from rpython.rlib.parsing.ebnfparse import parse_ebnf
from rpython.rlib.parsing.regexparse import parse_regex
from rpython.rlib.parsing.lexer import Lexer, DummyLexer
from rpython.rlib.parsing.deterministic import DFA
from rpython.rlib.parsing.tree import Nonterminal, Symbol, RPythonVisitor
from rpython.rlib.parsing.parsing import PackratParser, LazyParseTable, Rule
from rpython.rlib.parsing.regex import StringExpression
from pypy.objspace.std.strutil import string_to_int, ParseStringOverflowError, ParseStringError
from rpython.rlib.rarithmetic import ovfcheck
from pypy.objspace.std.strutil import string_to_int
from rpython.rlib.rbigint import rbigint
from prolog.interpreter.continuation import Engine
from prolog.interpreter.module import Module

def make_regexes():
    regexs = [
        ("VAR", parse_regex("[A-Z_]([a-zA-Z0-9]|_)*|_")),
        ("NUMBER", parse_regex("(0|[1-9][0-9]*)")),
        ("FLOAT", parse_regex("(0|[1-9][0-9]*)(\.[0-9]+)")),
        ("IGNORE", parse_regex(
            "[ \\n\\t\\r]|(/\\*[^\\*]*(\\*[^/][^\\*]*)*\\*+/)|(%[^\\n]*)")),
        ("ATOM", parse_regex("([a-z]([a-zA-Z0-9]|_)*)|('[^']*')|\[\]|!|\+|\-|\{\}")),
        ("STRING", parse_regex('"[^"]*"')),
        ("(", parse_regex("\(")),
        (")", parse_regex("\)")),
        ("[", parse_regex("\[")),
        ("]", parse_regex("\]")),
        ("{", parse_regex("\{")),
        ("}", parse_regex("\}")),
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
          ['FLOAT'],
          ['+', 'FLOAT'],
          ['-', 'FLOAT'],
          ['ATOM'],
          ['STRING'],
          ['(', 'toplevel_op_expr', ')'],
          ['{', 'toplevel_op_expr', '}'],
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
         (1150, [("fx",  ["meta_predicate"])]),
         (1100, [("xfy", [";"])]),
         (1050, [("xfy", ["->"]),
                 ("fx",  ["block"])]), 
         (1000, [("xfy", [","])]),
         (900,  [("fy",  ["\\+"]),
                 ("fx",  ["~"])]),
         (700,  [("xfx", ["<", "=", "=..", "=@=", "=:=", "=<", "==", "=\=", ">", "?=",
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
    def match_symbol(self, i, symbol):
        return LazyParseTable.match_symbol(self, i, symbol)

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
        if tok.name== ".":
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
    query = builder.build_query(s)
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
        from prolog.interpreter.term import Callable, Number, Float, BigInt
        children = []
        name = ""
        for child in node.children:
            if isinstance(child, Symbol):
                name = self.general_symbol_visit(child).name()            
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
            if isinstance(child, BigInt):
                return BigInt(rbigint.fromint(factor).mul(child.value))
        return Callable.build(name, children)

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
        from prolog.interpreter.term import Callable
        if node.additional_info.startswith("'"):
            end = len(node.additional_info) - 1
            assert end >= 0
            name = unescape(node.additional_info[1:end])
        else:
            name = node.additional_info
        return Callable.build(name)

    def visit_VAR(self, node):
        from prolog.interpreter.term import BindingVar
        varname = node.additional_info
        if varname == "_":
            return BindingVar()
        if varname in self.varname_to_var:
            return self.varname_to_var[varname]
        res = BindingVar()
        self.varname_to_var[varname] = res
        return res

    def visit_NUMBER(self, node):
        from prolog.interpreter.term import Number, BigInt
        s = node.additional_info
        try:
            intval = string_to_int(s)
        except ParseStringOverflowError: # overflow
            return BigInt(rbigint.fromdecimalstr(s))
        return Number(intval)

    def visit_FLOAT(self, node):
        from prolog.interpreter.term import Float
        s = node.additional_info
        return Float(float(s))

    def visit_STRING(self, node):
        from prolog.interpreter import helper
        from prolog.interpreter.term import Callable, Number
        from rpython.rlib.runicode import str_decode_utf_8
        info = node.additional_info
        s = info.strip('"')
        s, _ = str_decode_utf_8(s, len(s), 'strict')
        l = [Number(ord(c)) for c in s]
        return helper.wrap_list(l)

    def visit_complexterm(self, node):
        from prolog.interpreter.term import Callable
        name = self.general_symbol_visit(node.children[0]).name()
        children = self.build_list(node.children[2])
        return Callable.build(name, children[:])

    def visit_expr(self, node):
        from prolog.interpreter.term import Number, Float, BigInt
        additional_info = node.children[0].additional_info
        result = self.visit(node.children[1])
        if additional_info == '-':
            if isinstance(result, Number):
                return Number(-result.num)
            elif isinstance(result, Float):
                return Float(-result.floatval)
        elif additional_info == "{":
            from prolog.interpreter.term import Callable
            return Callable.build("{}", [result])
        return result

    def visit_listexpr(self, node):
        from prolog.interpreter.term import Callable
        node = node.children[1]
        if len(node.children) == 1:
            l = self.build_list(node)
            start = Callable.build("[]")
        else:
            l = self.build_list(node.children[0])
            start = self.visit(node.children[2])
        l.reverse()
        curr = start
        for elt in l:
            curr = Callable.build(".", [elt, curr])
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

def get_engine(source, create_files=False, load_system=False, **modules):
    from prolog.interpreter.continuation import Engine
    from prolog.interpreter.test.tool import create_file, delete_file
    e = Engine(load_system)
    for name, module in modules.iteritems():
        if create_files:
            create_file(name, module)
        else:
            e.runstring(module)
    try:
        e.modulewrapper.current_module = e.modulewrapper.user_module
        e.runstring(source)
    finally:
        if create_files:
            for name in modules.keys():
                delete_file(name)
    return e

# generated code between this line and its other occurence

parser_fact = PrologPackratParser([Rule('query', [['toplevel_op_expr', '.', 'EOF']]),
  Rule('fact', [['toplevel_op_expr', '.']]),
  Rule('complexterm', [['ATOM', '(', 'toplevel_op_expr', ')'], ['expr']]),
  Rule('expr', [['VAR'], ['NUMBER'], ['+', 'NUMBER'], ['-', 'NUMBER'], ['FLOAT'], ['+', 'FLOAT'], ['-', 'FLOAT'], ['ATOM'], ['STRING'], ['(', 'toplevel_op_expr', ')'], ['{', 'toplevel_op_expr', '}'], ['listexpr']]),
  Rule('listexpr', [['[', 'listbody', ']']]),
  Rule('listbody', [['toplevel_op_expr', '|', 'toplevel_op_expr'], ['toplevel_op_expr']]),
  Rule('extratoplevel_op_expr', [[]]),
  Rule('toplevel_op_expr', [['expr1150', '-->', 'expr1150', 'extratoplevel_op_expr'], ['expr1150', ':-', 'expr1150', 'extratoplevel_op_expr'], [':-', 'expr1150', 'extratoplevel_op_expr'], ['?-', 'expr1150', 'extratoplevel_op_expr'], ['expr1150', 'extratoplevel_op_expr']]),
  Rule('extraexpr1150', [[]]),
  Rule('expr1150', [['meta_predicate', 'expr1100', 'extraexpr1150'], ['expr1100', 'extraexpr1150']]),
  Rule('extraexpr1100', [[]]),
  Rule('expr1100', [['expr1050', ';', 'expr1100', 'extraexpr1100'], ['expr1050', 'extraexpr1100']]),
  Rule('extraexpr1050', [[]]),
  Rule('expr1050', [['expr1000', '->', 'expr1050', 'extraexpr1050'], ['block', 'expr1000', 'extraexpr1050'], ['expr1000', 'extraexpr1050']]),
  Rule('extraexpr1000', [[]]),
  Rule('expr1000', [['expr900', ',', 'expr1000', 'extraexpr1000'], ['expr900', 'extraexpr1000']]),
  Rule('extraexpr900', [[]]),
  Rule('expr900', [['\\+', 'expr900', 'extraexpr900'], ['~', 'expr700', 'extraexpr900'], ['expr700', 'extraexpr900']]),
  Rule('extraexpr700', [[]]),
  Rule('expr700', [['expr600', '<', 'expr600', 'extraexpr700'], ['expr600', '=', 'expr600', 'extraexpr700'], ['expr600', '=..', 'expr600', 'extraexpr700'], ['expr600', '=@=', 'expr600', 'extraexpr700'], ['expr600', '=:=', 'expr600', 'extraexpr700'], ['expr600', '=<', 'expr600', 'extraexpr700'], ['expr600', '==', 'expr600', 'extraexpr700'], ['expr600', '=\\=', 'expr600', 'extraexpr700'], ['expr600', '>', 'expr600', 'extraexpr700'], ['expr600', '?=', 'expr600', 'extraexpr700'], ['expr600', '>=', 'expr600', 'extraexpr700'], ['expr600', '@<', 'expr600', 'extraexpr700'], ['expr600', '@=<', 'expr600', 'extraexpr700'], ['expr600', '@>', 'expr600', 'extraexpr700'], ['expr600', '@>=', 'expr600', 'extraexpr700'], ['expr600', '\\=', 'expr600', 'extraexpr700'], ['expr600', '\\==', 'expr600', 'extraexpr700'], ['expr600', 'is', 'expr600', 'extraexpr700'], ['expr600', 'extraexpr700']]),
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
  Rule('expr', [['VAR'], ['NUMBER'], ['+', 'NUMBER'], ['-', 'NUMBER'], ['FLOAT'], ['+', 'FLOAT'], ['-', 'FLOAT'], ['ATOM'], ['STRING'], ['(', 'toplevel_op_expr', ')'], ['{', 'toplevel_op_expr', '}'], ['listexpr']]),
  Rule('listexpr', [['[', 'listbody', ']']]),
  Rule('listbody', [['toplevel_op_expr', '|', 'toplevel_op_expr'], ['toplevel_op_expr']]),
  Rule('extratoplevel_op_expr', [[]]),
  Rule('toplevel_op_expr', [['expr1150', '-->', 'expr1150', 'extratoplevel_op_expr'], ['expr1150', ':-', 'expr1150', 'extratoplevel_op_expr'], [':-', 'expr1150', 'extratoplevel_op_expr'], ['?-', 'expr1150', 'extratoplevel_op_expr'], ['expr1150', 'extratoplevel_op_expr']]),
  Rule('extraexpr1150', [[]]),
  Rule('expr1150', [['meta_predicate', 'expr1100', 'extraexpr1150'], ['expr1100', 'extraexpr1150']]),
  Rule('extraexpr1100', [[]]),
  Rule('expr1100', [['expr1050', ';', 'expr1100', 'extraexpr1100'], ['expr1050', 'extraexpr1100']]),
  Rule('extraexpr1050', [[]]),
  Rule('expr1050', [['expr1000', '->', 'expr1050', 'extraexpr1050'], ['block', 'expr1000', 'extraexpr1050'], ['expr1000', 'extraexpr1050']]),
  Rule('extraexpr1000', [[]]),
  Rule('expr1000', [['expr900', ',', 'expr1000', 'extraexpr1000'], ['expr900', 'extraexpr1000']]),
  Rule('extraexpr900', [[]]),
  Rule('expr900', [['\\+', 'expr900', 'extraexpr900'], ['~', 'expr700', 'extraexpr900'], ['expr700', 'extraexpr900']]),
  Rule('extraexpr700', [[]]),
  Rule('expr700', [['expr600', '<', 'expr600', 'extraexpr700'], ['expr600', '=', 'expr600', 'extraexpr700'], ['expr600', '=..', 'expr600', 'extraexpr700'], ['expr600', '=@=', 'expr600', 'extraexpr700'], ['expr600', '=:=', 'expr600', 'extraexpr700'], ['expr600', '=<', 'expr600', 'extraexpr700'], ['expr600', '==', 'expr600', 'extraexpr700'], ['expr600', '=\\=', 'expr600', 'extraexpr700'], ['expr600', '>', 'expr600', 'extraexpr700'], ['expr600', '?=', 'expr600', 'extraexpr700'], ['expr600', '>=', 'expr600', 'extraexpr700'], ['expr600', '@<', 'expr600', 'extraexpr700'], ['expr600', '@=<', 'expr600', 'extraexpr700'], ['expr600', '@>', 'expr600', 'extraexpr700'], ['expr600', '@>=', 'expr600', 'extraexpr700'], ['expr600', '\\=', 'expr600', 'extraexpr700'], ['expr600', '\\==', 'expr600', 'extraexpr700'], ['expr600', 'is', 'expr600', 'extraexpr700'], ['expr600', 'extraexpr700']]),
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
    #auto-generated code, don't edit
    assert i >= 0
    input = runner.text
    state = 0
    while 1:
        if state == 0:
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 0
                return ~i
            if char == '\t':
                state = 1
            elif char == '\n':
                state = 1
            elif char == '\r':
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
            elif 'c' <= char <= 'h':
                state = 10
            elif 's' <= char <= 'w':
                state = 10
            elif 'n' <= char <= 'q':
                state = 10
            elif 'j' <= char <= 'l':
                state = 10
            elif char == 'y':
                state = 10
            elif char == 'z':
                state = 10
            elif char == 'a':
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
            elif char == '{':
                state = 19
            elif char == '"':
                state = 20
            elif char == '*':
                state = 21
            elif char == '.':
                state = 22
            elif char == ':':
                state = 23
            elif char == '>':
                state = 24
            elif char == '^':
                state = 25
            elif char == 'b':
                state = 26
            elif char == 'r':
                state = 27
            elif char == '~':
                state = 28
            elif char == '!':
                state = 29
            elif char == '%':
                state = 30
            elif char == ')':
                state = 31
            elif char == '-':
                state = 32
            elif char == '=':
                state = 33
            elif char == ']':
                state = 34
            elif char == 'i':
                state = 35
            elif char == 'm':
                state = 36
            elif char == '}':
                state = 37
            else:
                break
        if state == 4:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 4
                return i
            if char == '.':
                state = 98
            else:
                break
        if state == 5:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 5
                return i
            if char == '.':
                state = 98
            elif '0' <= char <= '9':
                state = 5
                continue
            else:
                break
        if state == 6:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 6
                return i
            if char == '<':
                state = 97
            else:
                break
        if state == 7:
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 7
                return ~i
            if char == '=':
                state = 92
            elif char == '<':
                state = 93
            elif char == '>':
                state = 94
            else:
                break
        if state == 8:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 8
                return i
            if 'A' <= char <= 'Z':
                state = 8
                continue
            elif 'a' <= char <= 'z':
                state = 8
                continue
            elif '0' <= char <= '9':
                state = 8
                continue
            elif char == '_':
                state = 8
                continue
            else:
                break
        if state == 9:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 9
                return i
            if char == '+':
                state = 88
            elif char == '=':
                state = 89
            elif char == '/':
                state = 90
            else:
                break
        if state == 10:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 10
                return i
            if 'A' <= char <= 'Z':
                state = 10
                continue
            elif 'a' <= char <= 'z':
                state = 10
                continue
            elif '0' <= char <= '9':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            else:
                break
        if state == 11:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 11
                return i
            if 'A' <= char <= 'Z':
                state = 10
                continue
            elif 'a' <= char <= 'n':
                state = 10
                continue
            elif 'p' <= char <= 'z':
                state = 10
                continue
            elif '0' <= char <= '9':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            elif char == 'o':
                state = 86
            else:
                break
        if state == 13:
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 13
                return ~i
            if '(' <= char <= '\xff':
                state = 13
                continue
            elif '\x00' <= char <= '&':
                state = 13
                continue
            elif char == "'":
                state = 29
            else:
                break
        if state == 15:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 15
                return i
            if char == '*':
                state = 80
            elif char == '\\':
                state = 81
            elif char == '/':
                state = 82
            else:
                break
        if state == 17:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 17
                return i
            if char == '=':
                state = 78
            elif char == '-':
                state = 79
            else:
                break
        if state == 18:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 18
                return i
            if char == ']':
                state = 29
            else:
                break
        if state == 19:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 19
                return i
            if char == '}':
                state = 29
            else:
                break
        if state == 20:
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 20
                return ~i
            if '#' <= char <= '\xff':
                state = 20
                continue
            elif '\x00' <= char <= '!':
                state = 20
                continue
            elif char == '"':
                state = 77
            else:
                break
        if state == 21:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 21
                return i
            if char == '*':
                state = 76
            else:
                break
        if state == 23:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 23
                return i
            if char == '-':
                state = 75
            else:
                break
        if state == 24:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 24
                return i
            if char == '=':
                state = 73
            elif char == '>':
                state = 74
            else:
                break
        if state == 26:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 26
                return i
            if 'A' <= char <= 'Z':
                state = 10
                continue
            elif 'm' <= char <= 'z':
                state = 10
                continue
            elif 'a' <= char <= 'k':
                state = 10
                continue
            elif '0' <= char <= '9':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            elif char == 'l':
                state = 69
            else:
                break
        if state == 27:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 27
                return i
            if 'A' <= char <= 'Z':
                state = 10
                continue
            elif 'f' <= char <= 'z':
                state = 10
                continue
            elif '0' <= char <= '9':
                state = 10
                continue
            elif 'a' <= char <= 'd':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            elif char == 'e':
                state = 67
            else:
                break
        if state == 30:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 30
                return i
            if '\x0b' <= char <= '\xff':
                state = 30
                continue
            elif '\x00' <= char <= '\t':
                state = 30
                continue
            else:
                break
        if state == 32:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 32
                return i
            if char == '-':
                state = 64
            elif char == '>':
                state = 65
            else:
                break
        if state == 33:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 33
                return i
            if char == '@':
                state = 54
            elif char == '.':
                state = 55
            elif char == ':':
                state = 56
            elif char == '=':
                state = 57
            elif char == '<':
                state = 58
            elif char == '\\':
                state = 59
            else:
                break
        if state == 35:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 35
                return i
            if 'A' <= char <= 'Z':
                state = 10
                continue
            elif 'a' <= char <= 'r':
                state = 10
                continue
            elif '0' <= char <= '9':
                state = 10
                continue
            elif 't' <= char <= 'z':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            elif char == 's':
                state = 53
            else:
                break
        if state == 36:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 36
                return i
            if 'A' <= char <= 'Z':
                state = 10
                continue
            elif 'p' <= char <= 'z':
                state = 10
                continue
            elif '0' <= char <= '9':
                state = 10
                continue
            elif 'f' <= char <= 'n':
                state = 10
                continue
            elif 'a' <= char <= 'd':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            elif char == 'e':
                state = 38
            elif char == 'o':
                state = 39
            else:
                break
        if state == 38:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 38
                return i
            if char == 't':
                state = 41
            elif 'A' <= char <= 'Z':
                state = 10
                continue
            elif 'a' <= char <= 's':
                state = 10
                continue
            elif '0' <= char <= '9':
                state = 10
                continue
            elif 'u' <= char <= 'z':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            else:
                break
        if state == 39:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 39
                return i
            if char == 'd':
                state = 40
            elif 'A' <= char <= 'Z':
                state = 10
                continue
            elif 'e' <= char <= 'z':
                state = 10
                continue
            elif '0' <= char <= '9':
                state = 10
                continue
            elif 'a' <= char <= 'c':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            else:
                break
        if state == 40:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 40
                return i
            if 'A' <= char <= 'Z':
                state = 10
                continue
            elif 'a' <= char <= 'z':
                state = 10
                continue
            elif '0' <= char <= '9':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            else:
                break
        if state == 41:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 41
                return i
            if 'A' <= char <= 'Z':
                state = 10
                continue
            elif 'b' <= char <= 'z':
                state = 10
                continue
            elif '0' <= char <= '9':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            elif char == 'a':
                state = 42
            else:
                break
        if state == 42:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 42
                return i
            if 'A' <= char <= 'Z':
                state = 10
                continue
            elif 'a' <= char <= 'z':
                state = 10
                continue
            elif '0' <= char <= '9':
                state = 10
                continue
            elif char == '_':
                state = 43
            else:
                break
        if state == 43:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 43
                return i
            if 'A' <= char <= 'Z':
                state = 10
                continue
            elif 'a' <= char <= 'o':
                state = 10
                continue
            elif '0' <= char <= '9':
                state = 10
                continue
            elif 'q' <= char <= 'z':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            elif char == 'p':
                state = 44
            else:
                break
        if state == 44:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 44
                return i
            if 'A' <= char <= 'Z':
                state = 10
                continue
            elif 'a' <= char <= 'q':
                state = 10
                continue
            elif '0' <= char <= '9':
                state = 10
                continue
            elif 's' <= char <= 'z':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            elif char == 'r':
                state = 45
            else:
                break
        if state == 45:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 45
                return i
            if 'A' <= char <= 'Z':
                state = 10
                continue
            elif 'f' <= char <= 'z':
                state = 10
                continue
            elif '0' <= char <= '9':
                state = 10
                continue
            elif 'a' <= char <= 'd':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            elif char == 'e':
                state = 46
            else:
                break
        if state == 46:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 46
                return i
            if 'A' <= char <= 'Z':
                state = 10
                continue
            elif 'e' <= char <= 'z':
                state = 10
                continue
            elif '0' <= char <= '9':
                state = 10
                continue
            elif 'a' <= char <= 'c':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            elif char == 'd':
                state = 47
            else:
                break
        if state == 47:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 47
                return i
            if char == 'i':
                state = 48
            elif 'A' <= char <= 'Z':
                state = 10
                continue
            elif 'j' <= char <= 'z':
                state = 10
                continue
            elif '0' <= char <= '9':
                state = 10
                continue
            elif 'a' <= char <= 'h':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            else:
                break
        if state == 48:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 48
                return i
            if char == 'c':
                state = 49
            elif 'A' <= char <= 'Z':
                state = 10
                continue
            elif 'd' <= char <= 'z':
                state = 10
                continue
            elif '0' <= char <= '9':
                state = 10
                continue
            elif char == 'a':
                state = 10
                continue
            elif char == 'b':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            else:
                break
        if state == 49:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 49
                return i
            if 'A' <= char <= 'Z':
                state = 10
                continue
            elif 'b' <= char <= 'z':
                state = 10
                continue
            elif '0' <= char <= '9':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            elif char == 'a':
                state = 50
            else:
                break
        if state == 50:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 50
                return i
            if 'A' <= char <= 'Z':
                state = 10
                continue
            elif 'a' <= char <= 's':
                state = 10
                continue
            elif '0' <= char <= '9':
                state = 10
                continue
            elif 'u' <= char <= 'z':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            elif char == 't':
                state = 51
            else:
                break
        if state == 51:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 51
                return i
            if 'A' <= char <= 'Z':
                state = 10
                continue
            elif 'f' <= char <= 'z':
                state = 10
                continue
            elif '0' <= char <= '9':
                state = 10
                continue
            elif 'a' <= char <= 'd':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            elif char == 'e':
                state = 52
            else:
                break
        if state == 52:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 52
                return i
            if 'A' <= char <= 'Z':
                state = 10
                continue
            elif 'a' <= char <= 'z':
                state = 10
                continue
            elif '0' <= char <= '9':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            else:
                break
        if state == 53:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 53
                return i
            if 'A' <= char <= 'Z':
                state = 10
                continue
            elif 'a' <= char <= 'z':
                state = 10
                continue
            elif '0' <= char <= '9':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            else:
                break
        if state == 54:
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 54
                return ~i
            if char == '=':
                state = 63
            else:
                break
        if state == 55:
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 55
                return ~i
            if char == '.':
                state = 62
            else:
                break
        if state == 56:
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 56
                return ~i
            if char == '=':
                state = 61
            else:
                break
        if state == 59:
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 59
                return ~i
            if char == '=':
                state = 60
            else:
                break
        if state == 64:
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 64
                return ~i
            if char == '>':
                state = 66
            else:
                break
        if state == 67:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 67
                return i
            if 'A' <= char <= 'Z':
                state = 10
                continue
            elif 'n' <= char <= 'z':
                state = 10
                continue
            elif 'a' <= char <= 'l':
                state = 10
                continue
            elif '0' <= char <= '9':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            elif char == 'm':
                state = 68
            else:
                break
        if state == 68:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 68
                return i
            if 'A' <= char <= 'Z':
                state = 10
                continue
            elif 'a' <= char <= 'z':
                state = 10
                continue
            elif '0' <= char <= '9':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            else:
                break
        if state == 69:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 69
                return i
            if 'A' <= char <= 'Z':
                state = 10
                continue
            elif 'a' <= char <= 'n':
                state = 10
                continue
            elif 'p' <= char <= 'z':
                state = 10
                continue
            elif '0' <= char <= '9':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            elif char == 'o':
                state = 70
            else:
                break
        if state == 70:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 70
                return i
            if 'A' <= char <= 'Z':
                state = 10
                continue
            elif 'd' <= char <= 'z':
                state = 10
                continue
            elif '0' <= char <= '9':
                state = 10
                continue
            elif char == 'a':
                state = 10
                continue
            elif char == 'b':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            elif char == 'c':
                state = 71
            else:
                break
        if state == 71:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 71
                return i
            if char == 'k':
                state = 72
            elif 'A' <= char <= 'Z':
                state = 10
                continue
            elif 'l' <= char <= 'z':
                state = 10
                continue
            elif '0' <= char <= '9':
                state = 10
                continue
            elif 'a' <= char <= 'j':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            else:
                break
        if state == 72:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 72
                return i
            if 'A' <= char <= 'Z':
                state = 10
                continue
            elif 'a' <= char <= 'z':
                state = 10
                continue
            elif '0' <= char <= '9':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            else:
                break
        if state == 80:
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 80
                return ~i
            if '+' <= char <= '\xff':
                state = 80
                continue
            elif '\x00' <= char <= ')':
                state = 80
                continue
            elif char == '*':
                state = 83
            else:
                break
        if state == 83:
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 83
                return ~i
            if '0' <= char <= '\xff':
                state = 80
                continue
            elif '\x00' <= char <= ')':
                state = 80
                continue
            elif '+' <= char <= '.':
                state = 80
                continue
            elif char == '/':
                state = 1
            elif char == '*':
                state = 84
            else:
                break
        if state == 84:
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 84
                return ~i
            if '0' <= char <= '\xff':
                state = 80
                continue
            elif '\x00' <= char <= ')':
                state = 80
                continue
            elif '+' <= char <= '.':
                state = 80
                continue
            elif char == '*':
                state = 83
                continue
            elif char == '/':
                state = 85
            else:
                break
        if state == 85:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 85
                return i
            if '+' <= char <= '\xff':
                state = 80
                continue
            elif '\x00' <= char <= ')':
                state = 80
                continue
            elif char == '*':
                state = 83
                continue
            else:
                break
        if state == 86:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 86
                return i
            if 'A' <= char <= 'Z':
                state = 10
                continue
            elif 'a' <= char <= 'q':
                state = 10
                continue
            elif '0' <= char <= '9':
                state = 10
                continue
            elif 's' <= char <= 'z':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            elif char == 'r':
                state = 87
            else:
                break
        if state == 87:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 87
                return i
            if 'A' <= char <= 'Z':
                state = 10
                continue
            elif 'a' <= char <= 'z':
                state = 10
                continue
            elif '0' <= char <= '9':
                state = 10
                continue
            elif char == '_':
                state = 10
                continue
            else:
                break
        if state == 89:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 89
                return i
            if char == '=':
                state = 91
            else:
                break
        if state == 92:
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 92
                return ~i
            if char == '<':
                state = 96
            else:
                break
        if state == 94:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 94
                return i
            if char == '=':
                state = 95
            else:
                break
        if state == 98:
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 98
                return ~i
            if '0' <= char <= '9':
                state = 99
            else:
                break
        if state == 99:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            try:
                char = input[i]
                i += 1
            except IndexError:
                runner.state = 99
                return i
            if '0' <= char <= '9':
                state = 99
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
lexer = DummyLexer(recognize, DFA(100,
 {(0, '\t'): 1,
  (0, '\n'): 1,
  (0, '\r'): 1,
  (0, ' '): 1,
  (0, '!'): 29,
  (0, '"'): 20,
  (0, '%'): 30,
  (0, "'"): 13,
  (0, '('): 2,
  (0, ')'): 31,
  (0, '*'): 21,
  (0, '+'): 14,
  (0, ','): 3,
  (0, '-'): 32,
  (0, '.'): 22,
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
  (0, ':'): 23,
  (0, ';'): 16,
  (0, '<'): 6,
  (0, '='): 33,
  (0, '>'): 24,
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
  (0, ']'): 34,
  (0, '^'): 25,
  (0, '_'): 8,
  (0, 'a'): 10,
  (0, 'b'): 26,
  (0, 'c'): 10,
  (0, 'd'): 10,
  (0, 'e'): 10,
  (0, 'f'): 10,
  (0, 'g'): 10,
  (0, 'h'): 10,
  (0, 'i'): 35,
  (0, 'j'): 10,
  (0, 'k'): 10,
  (0, 'l'): 10,
  (0, 'm'): 36,
  (0, 'n'): 10,
  (0, 'o'): 10,
  (0, 'p'): 10,
  (0, 'q'): 10,
  (0, 'r'): 27,
  (0, 's'): 10,
  (0, 't'): 10,
  (0, 'u'): 10,
  (0, 'v'): 10,
  (0, 'w'): 10,
  (0, 'x'): 11,
  (0, 'y'): 10,
  (0, 'z'): 10,
  (0, '{'): 19,
  (0, '|'): 12,
  (0, '}'): 37,
  (0, '~'): 28,
  (4, '.'): 98,
  (5, '.'): 98,
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
  (6, '<'): 97,
  (7, '<'): 93,
  (7, '='): 92,
  (7, '>'): 94,
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
  (9, '+'): 88,
  (9, '/'): 90,
  (9, '='): 89,
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
  (11, 'o'): 86,
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
  (13, "'"): 29,
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
  (15, '*'): 80,
  (15, '/'): 82,
  (15, '\\'): 81,
  (17, '-'): 79,
  (17, '='): 78,
  (18, ']'): 29,
  (19, '}'): 29,
  (20, '\x00'): 20,
  (20, '\x01'): 20,
  (20, '\x02'): 20,
  (20, '\x03'): 20,
  (20, '\x04'): 20,
  (20, '\x05'): 20,
  (20, '\x06'): 20,
  (20, '\x07'): 20,
  (20, '\x08'): 20,
  (20, '\t'): 20,
  (20, '\n'): 20,
  (20, '\x0b'): 20,
  (20, '\x0c'): 20,
  (20, '\r'): 20,
  (20, '\x0e'): 20,
  (20, '\x0f'): 20,
  (20, '\x10'): 20,
  (20, '\x11'): 20,
  (20, '\x12'): 20,
  (20, '\x13'): 20,
  (20, '\x14'): 20,
  (20, '\x15'): 20,
  (20, '\x16'): 20,
  (20, '\x17'): 20,
  (20, '\x18'): 20,
  (20, '\x19'): 20,
  (20, '\x1a'): 20,
  (20, '\x1b'): 20,
  (20, '\x1c'): 20,
  (20, '\x1d'): 20,
  (20, '\x1e'): 20,
  (20, '\x1f'): 20,
  (20, ' '): 20,
  (20, '!'): 20,
  (20, '"'): 77,
  (20, '#'): 20,
  (20, '$'): 20,
  (20, '%'): 20,
  (20, '&'): 20,
  (20, "'"): 20,
  (20, '('): 20,
  (20, ')'): 20,
  (20, '*'): 20,
  (20, '+'): 20,
  (20, ','): 20,
  (20, '-'): 20,
  (20, '.'): 20,
  (20, '/'): 20,
  (20, '0'): 20,
  (20, '1'): 20,
  (20, '2'): 20,
  (20, '3'): 20,
  (20, '4'): 20,
  (20, '5'): 20,
  (20, '6'): 20,
  (20, '7'): 20,
  (20, '8'): 20,
  (20, '9'): 20,
  (20, ':'): 20,
  (20, ';'): 20,
  (20, '<'): 20,
  (20, '='): 20,
  (20, '>'): 20,
  (20, '?'): 20,
  (20, '@'): 20,
  (20, 'A'): 20,
  (20, 'B'): 20,
  (20, 'C'): 20,
  (20, 'D'): 20,
  (20, 'E'): 20,
  (20, 'F'): 20,
  (20, 'G'): 20,
  (20, 'H'): 20,
  (20, 'I'): 20,
  (20, 'J'): 20,
  (20, 'K'): 20,
  (20, 'L'): 20,
  (20, 'M'): 20,
  (20, 'N'): 20,
  (20, 'O'): 20,
  (20, 'P'): 20,
  (20, 'Q'): 20,
  (20, 'R'): 20,
  (20, 'S'): 20,
  (20, 'T'): 20,
  (20, 'U'): 20,
  (20, 'V'): 20,
  (20, 'W'): 20,
  (20, 'X'): 20,
  (20, 'Y'): 20,
  (20, 'Z'): 20,
  (20, '['): 20,
  (20, '\\'): 20,
  (20, ']'): 20,
  (20, '^'): 20,
  (20, '_'): 20,
  (20, '`'): 20,
  (20, 'a'): 20,
  (20, 'b'): 20,
  (20, 'c'): 20,
  (20, 'd'): 20,
  (20, 'e'): 20,
  (20, 'f'): 20,
  (20, 'g'): 20,
  (20, 'h'): 20,
  (20, 'i'): 20,
  (20, 'j'): 20,
  (20, 'k'): 20,
  (20, 'l'): 20,
  (20, 'm'): 20,
  (20, 'n'): 20,
  (20, 'o'): 20,
  (20, 'p'): 20,
  (20, 'q'): 20,
  (20, 'r'): 20,
  (20, 's'): 20,
  (20, 't'): 20,
  (20, 'u'): 20,
  (20, 'v'): 20,
  (20, 'w'): 20,
  (20, 'x'): 20,
  (20, 'y'): 20,
  (20, 'z'): 20,
  (20, '{'): 20,
  (20, '|'): 20,
  (20, '}'): 20,
  (20, '~'): 20,
  (20, '\x7f'): 20,
  (20, '\x80'): 20,
  (20, '\x81'): 20,
  (20, '\x82'): 20,
  (20, '\x83'): 20,
  (20, '\x84'): 20,
  (20, '\x85'): 20,
  (20, '\x86'): 20,
  (20, '\x87'): 20,
  (20, '\x88'): 20,
  (20, '\x89'): 20,
  (20, '\x8a'): 20,
  (20, '\x8b'): 20,
  (20, '\x8c'): 20,
  (20, '\x8d'): 20,
  (20, '\x8e'): 20,
  (20, '\x8f'): 20,
  (20, '\x90'): 20,
  (20, '\x91'): 20,
  (20, '\x92'): 20,
  (20, '\x93'): 20,
  (20, '\x94'): 20,
  (20, '\x95'): 20,
  (20, '\x96'): 20,
  (20, '\x97'): 20,
  (20, '\x98'): 20,
  (20, '\x99'): 20,
  (20, '\x9a'): 20,
  (20, '\x9b'): 20,
  (20, '\x9c'): 20,
  (20, '\x9d'): 20,
  (20, '\x9e'): 20,
  (20, '\x9f'): 20,
  (20, '\xa0'): 20,
  (20, '\xa1'): 20,
  (20, '\xa2'): 20,
  (20, '\xa3'): 20,
  (20, '\xa4'): 20,
  (20, '\xa5'): 20,
  (20, '\xa6'): 20,
  (20, '\xa7'): 20,
  (20, '\xa8'): 20,
  (20, '\xa9'): 20,
  (20, '\xaa'): 20,
  (20, '\xab'): 20,
  (20, '\xac'): 20,
  (20, '\xad'): 20,
  (20, '\xae'): 20,
  (20, '\xaf'): 20,
  (20, '\xb0'): 20,
  (20, '\xb1'): 20,
  (20, '\xb2'): 20,
  (20, '\xb3'): 20,
  (20, '\xb4'): 20,
  (20, '\xb5'): 20,
  (20, '\xb6'): 20,
  (20, '\xb7'): 20,
  (20, '\xb8'): 20,
  (20, '\xb9'): 20,
  (20, '\xba'): 20,
  (20, '\xbb'): 20,
  (20, '\xbc'): 20,
  (20, '\xbd'): 20,
  (20, '\xbe'): 20,
  (20, '\xbf'): 20,
  (20, '\xc0'): 20,
  (20, '\xc1'): 20,
  (20, '\xc2'): 20,
  (20, '\xc3'): 20,
  (20, '\xc4'): 20,
  (20, '\xc5'): 20,
  (20, '\xc6'): 20,
  (20, '\xc7'): 20,
  (20, '\xc8'): 20,
  (20, '\xc9'): 20,
  (20, '\xca'): 20,
  (20, '\xcb'): 20,
  (20, '\xcc'): 20,
  (20, '\xcd'): 20,
  (20, '\xce'): 20,
  (20, '\xcf'): 20,
  (20, '\xd0'): 20,
  (20, '\xd1'): 20,
  (20, '\xd2'): 20,
  (20, '\xd3'): 20,
  (20, '\xd4'): 20,
  (20, '\xd5'): 20,
  (20, '\xd6'): 20,
  (20, '\xd7'): 20,
  (20, '\xd8'): 20,
  (20, '\xd9'): 20,
  (20, '\xda'): 20,
  (20, '\xdb'): 20,
  (20, '\xdc'): 20,
  (20, '\xdd'): 20,
  (20, '\xde'): 20,
  (20, '\xdf'): 20,
  (20, '\xe0'): 20,
  (20, '\xe1'): 20,
  (20, '\xe2'): 20,
  (20, '\xe3'): 20,
  (20, '\xe4'): 20,
  (20, '\xe5'): 20,
  (20, '\xe6'): 20,
  (20, '\xe7'): 20,
  (20, '\xe8'): 20,
  (20, '\xe9'): 20,
  (20, '\xea'): 20,
  (20, '\xeb'): 20,
  (20, '\xec'): 20,
  (20, '\xed'): 20,
  (20, '\xee'): 20,
  (20, '\xef'): 20,
  (20, '\xf0'): 20,
  (20, '\xf1'): 20,
  (20, '\xf2'): 20,
  (20, '\xf3'): 20,
  (20, '\xf4'): 20,
  (20, '\xf5'): 20,
  (20, '\xf6'): 20,
  (20, '\xf7'): 20,
  (20, '\xf8'): 20,
  (20, '\xf9'): 20,
  (20, '\xfa'): 20,
  (20, '\xfb'): 20,
  (20, '\xfc'): 20,
  (20, '\xfd'): 20,
  (20, '\xfe'): 20,
  (20, '\xff'): 20,
  (21, '*'): 76,
  (23, '-'): 75,
  (24, '='): 73,
  (24, '>'): 74,
  (26, '0'): 10,
  (26, '1'): 10,
  (26, '2'): 10,
  (26, '3'): 10,
  (26, '4'): 10,
  (26, '5'): 10,
  (26, '6'): 10,
  (26, '7'): 10,
  (26, '8'): 10,
  (26, '9'): 10,
  (26, 'A'): 10,
  (26, 'B'): 10,
  (26, 'C'): 10,
  (26, 'D'): 10,
  (26, 'E'): 10,
  (26, 'F'): 10,
  (26, 'G'): 10,
  (26, 'H'): 10,
  (26, 'I'): 10,
  (26, 'J'): 10,
  (26, 'K'): 10,
  (26, 'L'): 10,
  (26, 'M'): 10,
  (26, 'N'): 10,
  (26, 'O'): 10,
  (26, 'P'): 10,
  (26, 'Q'): 10,
  (26, 'R'): 10,
  (26, 'S'): 10,
  (26, 'T'): 10,
  (26, 'U'): 10,
  (26, 'V'): 10,
  (26, 'W'): 10,
  (26, 'X'): 10,
  (26, 'Y'): 10,
  (26, 'Z'): 10,
  (26, '_'): 10,
  (26, 'a'): 10,
  (26, 'b'): 10,
  (26, 'c'): 10,
  (26, 'd'): 10,
  (26, 'e'): 10,
  (26, 'f'): 10,
  (26, 'g'): 10,
  (26, 'h'): 10,
  (26, 'i'): 10,
  (26, 'j'): 10,
  (26, 'k'): 10,
  (26, 'l'): 69,
  (26, 'm'): 10,
  (26, 'n'): 10,
  (26, 'o'): 10,
  (26, 'p'): 10,
  (26, 'q'): 10,
  (26, 'r'): 10,
  (26, 's'): 10,
  (26, 't'): 10,
  (26, 'u'): 10,
  (26, 'v'): 10,
  (26, 'w'): 10,
  (26, 'x'): 10,
  (26, 'y'): 10,
  (26, 'z'): 10,
  (27, '0'): 10,
  (27, '1'): 10,
  (27, '2'): 10,
  (27, '3'): 10,
  (27, '4'): 10,
  (27, '5'): 10,
  (27, '6'): 10,
  (27, '7'): 10,
  (27, '8'): 10,
  (27, '9'): 10,
  (27, 'A'): 10,
  (27, 'B'): 10,
  (27, 'C'): 10,
  (27, 'D'): 10,
  (27, 'E'): 10,
  (27, 'F'): 10,
  (27, 'G'): 10,
  (27, 'H'): 10,
  (27, 'I'): 10,
  (27, 'J'): 10,
  (27, 'K'): 10,
  (27, 'L'): 10,
  (27, 'M'): 10,
  (27, 'N'): 10,
  (27, 'O'): 10,
  (27, 'P'): 10,
  (27, 'Q'): 10,
  (27, 'R'): 10,
  (27, 'S'): 10,
  (27, 'T'): 10,
  (27, 'U'): 10,
  (27, 'V'): 10,
  (27, 'W'): 10,
  (27, 'X'): 10,
  (27, 'Y'): 10,
  (27, 'Z'): 10,
  (27, '_'): 10,
  (27, 'a'): 10,
  (27, 'b'): 10,
  (27, 'c'): 10,
  (27, 'd'): 10,
  (27, 'e'): 67,
  (27, 'f'): 10,
  (27, 'g'): 10,
  (27, 'h'): 10,
  (27, 'i'): 10,
  (27, 'j'): 10,
  (27, 'k'): 10,
  (27, 'l'): 10,
  (27, 'm'): 10,
  (27, 'n'): 10,
  (27, 'o'): 10,
  (27, 'p'): 10,
  (27, 'q'): 10,
  (27, 'r'): 10,
  (27, 's'): 10,
  (27, 't'): 10,
  (27, 'u'): 10,
  (27, 'v'): 10,
  (27, 'w'): 10,
  (27, 'x'): 10,
  (27, 'y'): 10,
  (27, 'z'): 10,
  (30, '\x00'): 30,
  (30, '\x01'): 30,
  (30, '\x02'): 30,
  (30, '\x03'): 30,
  (30, '\x04'): 30,
  (30, '\x05'): 30,
  (30, '\x06'): 30,
  (30, '\x07'): 30,
  (30, '\x08'): 30,
  (30, '\t'): 30,
  (30, '\x0b'): 30,
  (30, '\x0c'): 30,
  (30, '\r'): 30,
  (30, '\x0e'): 30,
  (30, '\x0f'): 30,
  (30, '\x10'): 30,
  (30, '\x11'): 30,
  (30, '\x12'): 30,
  (30, '\x13'): 30,
  (30, '\x14'): 30,
  (30, '\x15'): 30,
  (30, '\x16'): 30,
  (30, '\x17'): 30,
  (30, '\x18'): 30,
  (30, '\x19'): 30,
  (30, '\x1a'): 30,
  (30, '\x1b'): 30,
  (30, '\x1c'): 30,
  (30, '\x1d'): 30,
  (30, '\x1e'): 30,
  (30, '\x1f'): 30,
  (30, ' '): 30,
  (30, '!'): 30,
  (30, '"'): 30,
  (30, '#'): 30,
  (30, '$'): 30,
  (30, '%'): 30,
  (30, '&'): 30,
  (30, "'"): 30,
  (30, '('): 30,
  (30, ')'): 30,
  (30, '*'): 30,
  (30, '+'): 30,
  (30, ','): 30,
  (30, '-'): 30,
  (30, '.'): 30,
  (30, '/'): 30,
  (30, '0'): 30,
  (30, '1'): 30,
  (30, '2'): 30,
  (30, '3'): 30,
  (30, '4'): 30,
  (30, '5'): 30,
  (30, '6'): 30,
  (30, '7'): 30,
  (30, '8'): 30,
  (30, '9'): 30,
  (30, ':'): 30,
  (30, ';'): 30,
  (30, '<'): 30,
  (30, '='): 30,
  (30, '>'): 30,
  (30, '?'): 30,
  (30, '@'): 30,
  (30, 'A'): 30,
  (30, 'B'): 30,
  (30, 'C'): 30,
  (30, 'D'): 30,
  (30, 'E'): 30,
  (30, 'F'): 30,
  (30, 'G'): 30,
  (30, 'H'): 30,
  (30, 'I'): 30,
  (30, 'J'): 30,
  (30, 'K'): 30,
  (30, 'L'): 30,
  (30, 'M'): 30,
  (30, 'N'): 30,
  (30, 'O'): 30,
  (30, 'P'): 30,
  (30, 'Q'): 30,
  (30, 'R'): 30,
  (30, 'S'): 30,
  (30, 'T'): 30,
  (30, 'U'): 30,
  (30, 'V'): 30,
  (30, 'W'): 30,
  (30, 'X'): 30,
  (30, 'Y'): 30,
  (30, 'Z'): 30,
  (30, '['): 30,
  (30, '\\'): 30,
  (30, ']'): 30,
  (30, '^'): 30,
  (30, '_'): 30,
  (30, '`'): 30,
  (30, 'a'): 30,
  (30, 'b'): 30,
  (30, 'c'): 30,
  (30, 'd'): 30,
  (30, 'e'): 30,
  (30, 'f'): 30,
  (30, 'g'): 30,
  (30, 'h'): 30,
  (30, 'i'): 30,
  (30, 'j'): 30,
  (30, 'k'): 30,
  (30, 'l'): 30,
  (30, 'm'): 30,
  (30, 'n'): 30,
  (30, 'o'): 30,
  (30, 'p'): 30,
  (30, 'q'): 30,
  (30, 'r'): 30,
  (30, 's'): 30,
  (30, 't'): 30,
  (30, 'u'): 30,
  (30, 'v'): 30,
  (30, 'w'): 30,
  (30, 'x'): 30,
  (30, 'y'): 30,
  (30, 'z'): 30,
  (30, '{'): 30,
  (30, '|'): 30,
  (30, '}'): 30,
  (30, '~'): 30,
  (30, '\x7f'): 30,
  (30, '\x80'): 30,
  (30, '\x81'): 30,
  (30, '\x82'): 30,
  (30, '\x83'): 30,
  (30, '\x84'): 30,
  (30, '\x85'): 30,
  (30, '\x86'): 30,
  (30, '\x87'): 30,
  (30, '\x88'): 30,
  (30, '\x89'): 30,
  (30, '\x8a'): 30,
  (30, '\x8b'): 30,
  (30, '\x8c'): 30,
  (30, '\x8d'): 30,
  (30, '\x8e'): 30,
  (30, '\x8f'): 30,
  (30, '\x90'): 30,
  (30, '\x91'): 30,
  (30, '\x92'): 30,
  (30, '\x93'): 30,
  (30, '\x94'): 30,
  (30, '\x95'): 30,
  (30, '\x96'): 30,
  (30, '\x97'): 30,
  (30, '\x98'): 30,
  (30, '\x99'): 30,
  (30, '\x9a'): 30,
  (30, '\x9b'): 30,
  (30, '\x9c'): 30,
  (30, '\x9d'): 30,
  (30, '\x9e'): 30,
  (30, '\x9f'): 30,
  (30, '\xa0'): 30,
  (30, '\xa1'): 30,
  (30, '\xa2'): 30,
  (30, '\xa3'): 30,
  (30, '\xa4'): 30,
  (30, '\xa5'): 30,
  (30, '\xa6'): 30,
  (30, '\xa7'): 30,
  (30, '\xa8'): 30,
  (30, '\xa9'): 30,
  (30, '\xaa'): 30,
  (30, '\xab'): 30,
  (30, '\xac'): 30,
  (30, '\xad'): 30,
  (30, '\xae'): 30,
  (30, '\xaf'): 30,
  (30, '\xb0'): 30,
  (30, '\xb1'): 30,
  (30, '\xb2'): 30,
  (30, '\xb3'): 30,
  (30, '\xb4'): 30,
  (30, '\xb5'): 30,
  (30, '\xb6'): 30,
  (30, '\xb7'): 30,
  (30, '\xb8'): 30,
  (30, '\xb9'): 30,
  (30, '\xba'): 30,
  (30, '\xbb'): 30,
  (30, '\xbc'): 30,
  (30, '\xbd'): 30,
  (30, '\xbe'): 30,
  (30, '\xbf'): 30,
  (30, '\xc0'): 30,
  (30, '\xc1'): 30,
  (30, '\xc2'): 30,
  (30, '\xc3'): 30,
  (30, '\xc4'): 30,
  (30, '\xc5'): 30,
  (30, '\xc6'): 30,
  (30, '\xc7'): 30,
  (30, '\xc8'): 30,
  (30, '\xc9'): 30,
  (30, '\xca'): 30,
  (30, '\xcb'): 30,
  (30, '\xcc'): 30,
  (30, '\xcd'): 30,
  (30, '\xce'): 30,
  (30, '\xcf'): 30,
  (30, '\xd0'): 30,
  (30, '\xd1'): 30,
  (30, '\xd2'): 30,
  (30, '\xd3'): 30,
  (30, '\xd4'): 30,
  (30, '\xd5'): 30,
  (30, '\xd6'): 30,
  (30, '\xd7'): 30,
  (30, '\xd8'): 30,
  (30, '\xd9'): 30,
  (30, '\xda'): 30,
  (30, '\xdb'): 30,
  (30, '\xdc'): 30,
  (30, '\xdd'): 30,
  (30, '\xde'): 30,
  (30, '\xdf'): 30,
  (30, '\xe0'): 30,
  (30, '\xe1'): 30,
  (30, '\xe2'): 30,
  (30, '\xe3'): 30,
  (30, '\xe4'): 30,
  (30, '\xe5'): 30,
  (30, '\xe6'): 30,
  (30, '\xe7'): 30,
  (30, '\xe8'): 30,
  (30, '\xe9'): 30,
  (30, '\xea'): 30,
  (30, '\xeb'): 30,
  (30, '\xec'): 30,
  (30, '\xed'): 30,
  (30, '\xee'): 30,
  (30, '\xef'): 30,
  (30, '\xf0'): 30,
  (30, '\xf1'): 30,
  (30, '\xf2'): 30,
  (30, '\xf3'): 30,
  (30, '\xf4'): 30,
  (30, '\xf5'): 30,
  (30, '\xf6'): 30,
  (30, '\xf7'): 30,
  (30, '\xf8'): 30,
  (30, '\xf9'): 30,
  (30, '\xfa'): 30,
  (30, '\xfb'): 30,
  (30, '\xfc'): 30,
  (30, '\xfd'): 30,
  (30, '\xfe'): 30,
  (30, '\xff'): 30,
  (32, '-'): 64,
  (32, '>'): 65,
  (33, '.'): 55,
  (33, ':'): 56,
  (33, '<'): 58,
  (33, '='): 57,
  (33, '@'): 54,
  (33, '\\'): 59,
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
  (35, 's'): 53,
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
  (36, 'e'): 38,
  (36, 'f'): 10,
  (36, 'g'): 10,
  (36, 'h'): 10,
  (36, 'i'): 10,
  (36, 'j'): 10,
  (36, 'k'): 10,
  (36, 'l'): 10,
  (36, 'm'): 10,
  (36, 'n'): 10,
  (36, 'o'): 39,
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
  (38, '0'): 10,
  (38, '1'): 10,
  (38, '2'): 10,
  (38, '3'): 10,
  (38, '4'): 10,
  (38, '5'): 10,
  (38, '6'): 10,
  (38, '7'): 10,
  (38, '8'): 10,
  (38, '9'): 10,
  (38, 'A'): 10,
  (38, 'B'): 10,
  (38, 'C'): 10,
  (38, 'D'): 10,
  (38, 'E'): 10,
  (38, 'F'): 10,
  (38, 'G'): 10,
  (38, 'H'): 10,
  (38, 'I'): 10,
  (38, 'J'): 10,
  (38, 'K'): 10,
  (38, 'L'): 10,
  (38, 'M'): 10,
  (38, 'N'): 10,
  (38, 'O'): 10,
  (38, 'P'): 10,
  (38, 'Q'): 10,
  (38, 'R'): 10,
  (38, 'S'): 10,
  (38, 'T'): 10,
  (38, 'U'): 10,
  (38, 'V'): 10,
  (38, 'W'): 10,
  (38, 'X'): 10,
  (38, 'Y'): 10,
  (38, 'Z'): 10,
  (38, '_'): 10,
  (38, 'a'): 10,
  (38, 'b'): 10,
  (38, 'c'): 10,
  (38, 'd'): 10,
  (38, 'e'): 10,
  (38, 'f'): 10,
  (38, 'g'): 10,
  (38, 'h'): 10,
  (38, 'i'): 10,
  (38, 'j'): 10,
  (38, 'k'): 10,
  (38, 'l'): 10,
  (38, 'm'): 10,
  (38, 'n'): 10,
  (38, 'o'): 10,
  (38, 'p'): 10,
  (38, 'q'): 10,
  (38, 'r'): 10,
  (38, 's'): 10,
  (38, 't'): 41,
  (38, 'u'): 10,
  (38, 'v'): 10,
  (38, 'w'): 10,
  (38, 'x'): 10,
  (38, 'y'): 10,
  (38, 'z'): 10,
  (39, '0'): 10,
  (39, '1'): 10,
  (39, '2'): 10,
  (39, '3'): 10,
  (39, '4'): 10,
  (39, '5'): 10,
  (39, '6'): 10,
  (39, '7'): 10,
  (39, '8'): 10,
  (39, '9'): 10,
  (39, 'A'): 10,
  (39, 'B'): 10,
  (39, 'C'): 10,
  (39, 'D'): 10,
  (39, 'E'): 10,
  (39, 'F'): 10,
  (39, 'G'): 10,
  (39, 'H'): 10,
  (39, 'I'): 10,
  (39, 'J'): 10,
  (39, 'K'): 10,
  (39, 'L'): 10,
  (39, 'M'): 10,
  (39, 'N'): 10,
  (39, 'O'): 10,
  (39, 'P'): 10,
  (39, 'Q'): 10,
  (39, 'R'): 10,
  (39, 'S'): 10,
  (39, 'T'): 10,
  (39, 'U'): 10,
  (39, 'V'): 10,
  (39, 'W'): 10,
  (39, 'X'): 10,
  (39, 'Y'): 10,
  (39, 'Z'): 10,
  (39, '_'): 10,
  (39, 'a'): 10,
  (39, 'b'): 10,
  (39, 'c'): 10,
  (39, 'd'): 40,
  (39, 'e'): 10,
  (39, 'f'): 10,
  (39, 'g'): 10,
  (39, 'h'): 10,
  (39, 'i'): 10,
  (39, 'j'): 10,
  (39, 'k'): 10,
  (39, 'l'): 10,
  (39, 'm'): 10,
  (39, 'n'): 10,
  (39, 'o'): 10,
  (39, 'p'): 10,
  (39, 'q'): 10,
  (39, 'r'): 10,
  (39, 's'): 10,
  (39, 't'): 10,
  (39, 'u'): 10,
  (39, 'v'): 10,
  (39, 'w'): 10,
  (39, 'x'): 10,
  (39, 'y'): 10,
  (39, 'z'): 10,
  (40, '0'): 10,
  (40, '1'): 10,
  (40, '2'): 10,
  (40, '3'): 10,
  (40, '4'): 10,
  (40, '5'): 10,
  (40, '6'): 10,
  (40, '7'): 10,
  (40, '8'): 10,
  (40, '9'): 10,
  (40, 'A'): 10,
  (40, 'B'): 10,
  (40, 'C'): 10,
  (40, 'D'): 10,
  (40, 'E'): 10,
  (40, 'F'): 10,
  (40, 'G'): 10,
  (40, 'H'): 10,
  (40, 'I'): 10,
  (40, 'J'): 10,
  (40, 'K'): 10,
  (40, 'L'): 10,
  (40, 'M'): 10,
  (40, 'N'): 10,
  (40, 'O'): 10,
  (40, 'P'): 10,
  (40, 'Q'): 10,
  (40, 'R'): 10,
  (40, 'S'): 10,
  (40, 'T'): 10,
  (40, 'U'): 10,
  (40, 'V'): 10,
  (40, 'W'): 10,
  (40, 'X'): 10,
  (40, 'Y'): 10,
  (40, 'Z'): 10,
  (40, '_'): 10,
  (40, 'a'): 10,
  (40, 'b'): 10,
  (40, 'c'): 10,
  (40, 'd'): 10,
  (40, 'e'): 10,
  (40, 'f'): 10,
  (40, 'g'): 10,
  (40, 'h'): 10,
  (40, 'i'): 10,
  (40, 'j'): 10,
  (40, 'k'): 10,
  (40, 'l'): 10,
  (40, 'm'): 10,
  (40, 'n'): 10,
  (40, 'o'): 10,
  (40, 'p'): 10,
  (40, 'q'): 10,
  (40, 'r'): 10,
  (40, 's'): 10,
  (40, 't'): 10,
  (40, 'u'): 10,
  (40, 'v'): 10,
  (40, 'w'): 10,
  (40, 'x'): 10,
  (40, 'y'): 10,
  (40, 'z'): 10,
  (41, '0'): 10,
  (41, '1'): 10,
  (41, '2'): 10,
  (41, '3'): 10,
  (41, '4'): 10,
  (41, '5'): 10,
  (41, '6'): 10,
  (41, '7'): 10,
  (41, '8'): 10,
  (41, '9'): 10,
  (41, 'A'): 10,
  (41, 'B'): 10,
  (41, 'C'): 10,
  (41, 'D'): 10,
  (41, 'E'): 10,
  (41, 'F'): 10,
  (41, 'G'): 10,
  (41, 'H'): 10,
  (41, 'I'): 10,
  (41, 'J'): 10,
  (41, 'K'): 10,
  (41, 'L'): 10,
  (41, 'M'): 10,
  (41, 'N'): 10,
  (41, 'O'): 10,
  (41, 'P'): 10,
  (41, 'Q'): 10,
  (41, 'R'): 10,
  (41, 'S'): 10,
  (41, 'T'): 10,
  (41, 'U'): 10,
  (41, 'V'): 10,
  (41, 'W'): 10,
  (41, 'X'): 10,
  (41, 'Y'): 10,
  (41, 'Z'): 10,
  (41, '_'): 10,
  (41, 'a'): 42,
  (41, 'b'): 10,
  (41, 'c'): 10,
  (41, 'd'): 10,
  (41, 'e'): 10,
  (41, 'f'): 10,
  (41, 'g'): 10,
  (41, 'h'): 10,
  (41, 'i'): 10,
  (41, 'j'): 10,
  (41, 'k'): 10,
  (41, 'l'): 10,
  (41, 'm'): 10,
  (41, 'n'): 10,
  (41, 'o'): 10,
  (41, 'p'): 10,
  (41, 'q'): 10,
  (41, 'r'): 10,
  (41, 's'): 10,
  (41, 't'): 10,
  (41, 'u'): 10,
  (41, 'v'): 10,
  (41, 'w'): 10,
  (41, 'x'): 10,
  (41, 'y'): 10,
  (41, 'z'): 10,
  (42, '0'): 10,
  (42, '1'): 10,
  (42, '2'): 10,
  (42, '3'): 10,
  (42, '4'): 10,
  (42, '5'): 10,
  (42, '6'): 10,
  (42, '7'): 10,
  (42, '8'): 10,
  (42, '9'): 10,
  (42, 'A'): 10,
  (42, 'B'): 10,
  (42, 'C'): 10,
  (42, 'D'): 10,
  (42, 'E'): 10,
  (42, 'F'): 10,
  (42, 'G'): 10,
  (42, 'H'): 10,
  (42, 'I'): 10,
  (42, 'J'): 10,
  (42, 'K'): 10,
  (42, 'L'): 10,
  (42, 'M'): 10,
  (42, 'N'): 10,
  (42, 'O'): 10,
  (42, 'P'): 10,
  (42, 'Q'): 10,
  (42, 'R'): 10,
  (42, 'S'): 10,
  (42, 'T'): 10,
  (42, 'U'): 10,
  (42, 'V'): 10,
  (42, 'W'): 10,
  (42, 'X'): 10,
  (42, 'Y'): 10,
  (42, 'Z'): 10,
  (42, '_'): 43,
  (42, 'a'): 10,
  (42, 'b'): 10,
  (42, 'c'): 10,
  (42, 'd'): 10,
  (42, 'e'): 10,
  (42, 'f'): 10,
  (42, 'g'): 10,
  (42, 'h'): 10,
  (42, 'i'): 10,
  (42, 'j'): 10,
  (42, 'k'): 10,
  (42, 'l'): 10,
  (42, 'm'): 10,
  (42, 'n'): 10,
  (42, 'o'): 10,
  (42, 'p'): 10,
  (42, 'q'): 10,
  (42, 'r'): 10,
  (42, 's'): 10,
  (42, 't'): 10,
  (42, 'u'): 10,
  (42, 'v'): 10,
  (42, 'w'): 10,
  (42, 'x'): 10,
  (42, 'y'): 10,
  (42, 'z'): 10,
  (43, '0'): 10,
  (43, '1'): 10,
  (43, '2'): 10,
  (43, '3'): 10,
  (43, '4'): 10,
  (43, '5'): 10,
  (43, '6'): 10,
  (43, '7'): 10,
  (43, '8'): 10,
  (43, '9'): 10,
  (43, 'A'): 10,
  (43, 'B'): 10,
  (43, 'C'): 10,
  (43, 'D'): 10,
  (43, 'E'): 10,
  (43, 'F'): 10,
  (43, 'G'): 10,
  (43, 'H'): 10,
  (43, 'I'): 10,
  (43, 'J'): 10,
  (43, 'K'): 10,
  (43, 'L'): 10,
  (43, 'M'): 10,
  (43, 'N'): 10,
  (43, 'O'): 10,
  (43, 'P'): 10,
  (43, 'Q'): 10,
  (43, 'R'): 10,
  (43, 'S'): 10,
  (43, 'T'): 10,
  (43, 'U'): 10,
  (43, 'V'): 10,
  (43, 'W'): 10,
  (43, 'X'): 10,
  (43, 'Y'): 10,
  (43, 'Z'): 10,
  (43, '_'): 10,
  (43, 'a'): 10,
  (43, 'b'): 10,
  (43, 'c'): 10,
  (43, 'd'): 10,
  (43, 'e'): 10,
  (43, 'f'): 10,
  (43, 'g'): 10,
  (43, 'h'): 10,
  (43, 'i'): 10,
  (43, 'j'): 10,
  (43, 'k'): 10,
  (43, 'l'): 10,
  (43, 'm'): 10,
  (43, 'n'): 10,
  (43, 'o'): 10,
  (43, 'p'): 44,
  (43, 'q'): 10,
  (43, 'r'): 10,
  (43, 's'): 10,
  (43, 't'): 10,
  (43, 'u'): 10,
  (43, 'v'): 10,
  (43, 'w'): 10,
  (43, 'x'): 10,
  (43, 'y'): 10,
  (43, 'z'): 10,
  (44, '0'): 10,
  (44, '1'): 10,
  (44, '2'): 10,
  (44, '3'): 10,
  (44, '4'): 10,
  (44, '5'): 10,
  (44, '6'): 10,
  (44, '7'): 10,
  (44, '8'): 10,
  (44, '9'): 10,
  (44, 'A'): 10,
  (44, 'B'): 10,
  (44, 'C'): 10,
  (44, 'D'): 10,
  (44, 'E'): 10,
  (44, 'F'): 10,
  (44, 'G'): 10,
  (44, 'H'): 10,
  (44, 'I'): 10,
  (44, 'J'): 10,
  (44, 'K'): 10,
  (44, 'L'): 10,
  (44, 'M'): 10,
  (44, 'N'): 10,
  (44, 'O'): 10,
  (44, 'P'): 10,
  (44, 'Q'): 10,
  (44, 'R'): 10,
  (44, 'S'): 10,
  (44, 'T'): 10,
  (44, 'U'): 10,
  (44, 'V'): 10,
  (44, 'W'): 10,
  (44, 'X'): 10,
  (44, 'Y'): 10,
  (44, 'Z'): 10,
  (44, '_'): 10,
  (44, 'a'): 10,
  (44, 'b'): 10,
  (44, 'c'): 10,
  (44, 'd'): 10,
  (44, 'e'): 10,
  (44, 'f'): 10,
  (44, 'g'): 10,
  (44, 'h'): 10,
  (44, 'i'): 10,
  (44, 'j'): 10,
  (44, 'k'): 10,
  (44, 'l'): 10,
  (44, 'm'): 10,
  (44, 'n'): 10,
  (44, 'o'): 10,
  (44, 'p'): 10,
  (44, 'q'): 10,
  (44, 'r'): 45,
  (44, 's'): 10,
  (44, 't'): 10,
  (44, 'u'): 10,
  (44, 'v'): 10,
  (44, 'w'): 10,
  (44, 'x'): 10,
  (44, 'y'): 10,
  (44, 'z'): 10,
  (45, '0'): 10,
  (45, '1'): 10,
  (45, '2'): 10,
  (45, '3'): 10,
  (45, '4'): 10,
  (45, '5'): 10,
  (45, '6'): 10,
  (45, '7'): 10,
  (45, '8'): 10,
  (45, '9'): 10,
  (45, 'A'): 10,
  (45, 'B'): 10,
  (45, 'C'): 10,
  (45, 'D'): 10,
  (45, 'E'): 10,
  (45, 'F'): 10,
  (45, 'G'): 10,
  (45, 'H'): 10,
  (45, 'I'): 10,
  (45, 'J'): 10,
  (45, 'K'): 10,
  (45, 'L'): 10,
  (45, 'M'): 10,
  (45, 'N'): 10,
  (45, 'O'): 10,
  (45, 'P'): 10,
  (45, 'Q'): 10,
  (45, 'R'): 10,
  (45, 'S'): 10,
  (45, 'T'): 10,
  (45, 'U'): 10,
  (45, 'V'): 10,
  (45, 'W'): 10,
  (45, 'X'): 10,
  (45, 'Y'): 10,
  (45, 'Z'): 10,
  (45, '_'): 10,
  (45, 'a'): 10,
  (45, 'b'): 10,
  (45, 'c'): 10,
  (45, 'd'): 10,
  (45, 'e'): 46,
  (45, 'f'): 10,
  (45, 'g'): 10,
  (45, 'h'): 10,
  (45, 'i'): 10,
  (45, 'j'): 10,
  (45, 'k'): 10,
  (45, 'l'): 10,
  (45, 'm'): 10,
  (45, 'n'): 10,
  (45, 'o'): 10,
  (45, 'p'): 10,
  (45, 'q'): 10,
  (45, 'r'): 10,
  (45, 's'): 10,
  (45, 't'): 10,
  (45, 'u'): 10,
  (45, 'v'): 10,
  (45, 'w'): 10,
  (45, 'x'): 10,
  (45, 'y'): 10,
  (45, 'z'): 10,
  (46, '0'): 10,
  (46, '1'): 10,
  (46, '2'): 10,
  (46, '3'): 10,
  (46, '4'): 10,
  (46, '5'): 10,
  (46, '6'): 10,
  (46, '7'): 10,
  (46, '8'): 10,
  (46, '9'): 10,
  (46, 'A'): 10,
  (46, 'B'): 10,
  (46, 'C'): 10,
  (46, 'D'): 10,
  (46, 'E'): 10,
  (46, 'F'): 10,
  (46, 'G'): 10,
  (46, 'H'): 10,
  (46, 'I'): 10,
  (46, 'J'): 10,
  (46, 'K'): 10,
  (46, 'L'): 10,
  (46, 'M'): 10,
  (46, 'N'): 10,
  (46, 'O'): 10,
  (46, 'P'): 10,
  (46, 'Q'): 10,
  (46, 'R'): 10,
  (46, 'S'): 10,
  (46, 'T'): 10,
  (46, 'U'): 10,
  (46, 'V'): 10,
  (46, 'W'): 10,
  (46, 'X'): 10,
  (46, 'Y'): 10,
  (46, 'Z'): 10,
  (46, '_'): 10,
  (46, 'a'): 10,
  (46, 'b'): 10,
  (46, 'c'): 10,
  (46, 'd'): 47,
  (46, 'e'): 10,
  (46, 'f'): 10,
  (46, 'g'): 10,
  (46, 'h'): 10,
  (46, 'i'): 10,
  (46, 'j'): 10,
  (46, 'k'): 10,
  (46, 'l'): 10,
  (46, 'm'): 10,
  (46, 'n'): 10,
  (46, 'o'): 10,
  (46, 'p'): 10,
  (46, 'q'): 10,
  (46, 'r'): 10,
  (46, 's'): 10,
  (46, 't'): 10,
  (46, 'u'): 10,
  (46, 'v'): 10,
  (46, 'w'): 10,
  (46, 'x'): 10,
  (46, 'y'): 10,
  (46, 'z'): 10,
  (47, '0'): 10,
  (47, '1'): 10,
  (47, '2'): 10,
  (47, '3'): 10,
  (47, '4'): 10,
  (47, '5'): 10,
  (47, '6'): 10,
  (47, '7'): 10,
  (47, '8'): 10,
  (47, '9'): 10,
  (47, 'A'): 10,
  (47, 'B'): 10,
  (47, 'C'): 10,
  (47, 'D'): 10,
  (47, 'E'): 10,
  (47, 'F'): 10,
  (47, 'G'): 10,
  (47, 'H'): 10,
  (47, 'I'): 10,
  (47, 'J'): 10,
  (47, 'K'): 10,
  (47, 'L'): 10,
  (47, 'M'): 10,
  (47, 'N'): 10,
  (47, 'O'): 10,
  (47, 'P'): 10,
  (47, 'Q'): 10,
  (47, 'R'): 10,
  (47, 'S'): 10,
  (47, 'T'): 10,
  (47, 'U'): 10,
  (47, 'V'): 10,
  (47, 'W'): 10,
  (47, 'X'): 10,
  (47, 'Y'): 10,
  (47, 'Z'): 10,
  (47, '_'): 10,
  (47, 'a'): 10,
  (47, 'b'): 10,
  (47, 'c'): 10,
  (47, 'd'): 10,
  (47, 'e'): 10,
  (47, 'f'): 10,
  (47, 'g'): 10,
  (47, 'h'): 10,
  (47, 'i'): 48,
  (47, 'j'): 10,
  (47, 'k'): 10,
  (47, 'l'): 10,
  (47, 'm'): 10,
  (47, 'n'): 10,
  (47, 'o'): 10,
  (47, 'p'): 10,
  (47, 'q'): 10,
  (47, 'r'): 10,
  (47, 's'): 10,
  (47, 't'): 10,
  (47, 'u'): 10,
  (47, 'v'): 10,
  (47, 'w'): 10,
  (47, 'x'): 10,
  (47, 'y'): 10,
  (47, 'z'): 10,
  (48, '0'): 10,
  (48, '1'): 10,
  (48, '2'): 10,
  (48, '3'): 10,
  (48, '4'): 10,
  (48, '5'): 10,
  (48, '6'): 10,
  (48, '7'): 10,
  (48, '8'): 10,
  (48, '9'): 10,
  (48, 'A'): 10,
  (48, 'B'): 10,
  (48, 'C'): 10,
  (48, 'D'): 10,
  (48, 'E'): 10,
  (48, 'F'): 10,
  (48, 'G'): 10,
  (48, 'H'): 10,
  (48, 'I'): 10,
  (48, 'J'): 10,
  (48, 'K'): 10,
  (48, 'L'): 10,
  (48, 'M'): 10,
  (48, 'N'): 10,
  (48, 'O'): 10,
  (48, 'P'): 10,
  (48, 'Q'): 10,
  (48, 'R'): 10,
  (48, 'S'): 10,
  (48, 'T'): 10,
  (48, 'U'): 10,
  (48, 'V'): 10,
  (48, 'W'): 10,
  (48, 'X'): 10,
  (48, 'Y'): 10,
  (48, 'Z'): 10,
  (48, '_'): 10,
  (48, 'a'): 10,
  (48, 'b'): 10,
  (48, 'c'): 49,
  (48, 'd'): 10,
  (48, 'e'): 10,
  (48, 'f'): 10,
  (48, 'g'): 10,
  (48, 'h'): 10,
  (48, 'i'): 10,
  (48, 'j'): 10,
  (48, 'k'): 10,
  (48, 'l'): 10,
  (48, 'm'): 10,
  (48, 'n'): 10,
  (48, 'o'): 10,
  (48, 'p'): 10,
  (48, 'q'): 10,
  (48, 'r'): 10,
  (48, 's'): 10,
  (48, 't'): 10,
  (48, 'u'): 10,
  (48, 'v'): 10,
  (48, 'w'): 10,
  (48, 'x'): 10,
  (48, 'y'): 10,
  (48, 'z'): 10,
  (49, '0'): 10,
  (49, '1'): 10,
  (49, '2'): 10,
  (49, '3'): 10,
  (49, '4'): 10,
  (49, '5'): 10,
  (49, '6'): 10,
  (49, '7'): 10,
  (49, '8'): 10,
  (49, '9'): 10,
  (49, 'A'): 10,
  (49, 'B'): 10,
  (49, 'C'): 10,
  (49, 'D'): 10,
  (49, 'E'): 10,
  (49, 'F'): 10,
  (49, 'G'): 10,
  (49, 'H'): 10,
  (49, 'I'): 10,
  (49, 'J'): 10,
  (49, 'K'): 10,
  (49, 'L'): 10,
  (49, 'M'): 10,
  (49, 'N'): 10,
  (49, 'O'): 10,
  (49, 'P'): 10,
  (49, 'Q'): 10,
  (49, 'R'): 10,
  (49, 'S'): 10,
  (49, 'T'): 10,
  (49, 'U'): 10,
  (49, 'V'): 10,
  (49, 'W'): 10,
  (49, 'X'): 10,
  (49, 'Y'): 10,
  (49, 'Z'): 10,
  (49, '_'): 10,
  (49, 'a'): 50,
  (49, 'b'): 10,
  (49, 'c'): 10,
  (49, 'd'): 10,
  (49, 'e'): 10,
  (49, 'f'): 10,
  (49, 'g'): 10,
  (49, 'h'): 10,
  (49, 'i'): 10,
  (49, 'j'): 10,
  (49, 'k'): 10,
  (49, 'l'): 10,
  (49, 'm'): 10,
  (49, 'n'): 10,
  (49, 'o'): 10,
  (49, 'p'): 10,
  (49, 'q'): 10,
  (49, 'r'): 10,
  (49, 's'): 10,
  (49, 't'): 10,
  (49, 'u'): 10,
  (49, 'v'): 10,
  (49, 'w'): 10,
  (49, 'x'): 10,
  (49, 'y'): 10,
  (49, 'z'): 10,
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
  (50, 'm'): 10,
  (50, 'n'): 10,
  (50, 'o'): 10,
  (50, 'p'): 10,
  (50, 'q'): 10,
  (50, 'r'): 10,
  (50, 's'): 10,
  (50, 't'): 51,
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
  (51, 'e'): 52,
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
  (52, '0'): 10,
  (52, '1'): 10,
  (52, '2'): 10,
  (52, '3'): 10,
  (52, '4'): 10,
  (52, '5'): 10,
  (52, '6'): 10,
  (52, '7'): 10,
  (52, '8'): 10,
  (52, '9'): 10,
  (52, 'A'): 10,
  (52, 'B'): 10,
  (52, 'C'): 10,
  (52, 'D'): 10,
  (52, 'E'): 10,
  (52, 'F'): 10,
  (52, 'G'): 10,
  (52, 'H'): 10,
  (52, 'I'): 10,
  (52, 'J'): 10,
  (52, 'K'): 10,
  (52, 'L'): 10,
  (52, 'M'): 10,
  (52, 'N'): 10,
  (52, 'O'): 10,
  (52, 'P'): 10,
  (52, 'Q'): 10,
  (52, 'R'): 10,
  (52, 'S'): 10,
  (52, 'T'): 10,
  (52, 'U'): 10,
  (52, 'V'): 10,
  (52, 'W'): 10,
  (52, 'X'): 10,
  (52, 'Y'): 10,
  (52, 'Z'): 10,
  (52, '_'): 10,
  (52, 'a'): 10,
  (52, 'b'): 10,
  (52, 'c'): 10,
  (52, 'd'): 10,
  (52, 'e'): 10,
  (52, 'f'): 10,
  (52, 'g'): 10,
  (52, 'h'): 10,
  (52, 'i'): 10,
  (52, 'j'): 10,
  (52, 'k'): 10,
  (52, 'l'): 10,
  (52, 'm'): 10,
  (52, 'n'): 10,
  (52, 'o'): 10,
  (52, 'p'): 10,
  (52, 'q'): 10,
  (52, 'r'): 10,
  (52, 's'): 10,
  (52, 't'): 10,
  (52, 'u'): 10,
  (52, 'v'): 10,
  (52, 'w'): 10,
  (52, 'x'): 10,
  (52, 'y'): 10,
  (52, 'z'): 10,
  (53, '0'): 10,
  (53, '1'): 10,
  (53, '2'): 10,
  (53, '3'): 10,
  (53, '4'): 10,
  (53, '5'): 10,
  (53, '6'): 10,
  (53, '7'): 10,
  (53, '8'): 10,
  (53, '9'): 10,
  (53, 'A'): 10,
  (53, 'B'): 10,
  (53, 'C'): 10,
  (53, 'D'): 10,
  (53, 'E'): 10,
  (53, 'F'): 10,
  (53, 'G'): 10,
  (53, 'H'): 10,
  (53, 'I'): 10,
  (53, 'J'): 10,
  (53, 'K'): 10,
  (53, 'L'): 10,
  (53, 'M'): 10,
  (53, 'N'): 10,
  (53, 'O'): 10,
  (53, 'P'): 10,
  (53, 'Q'): 10,
  (53, 'R'): 10,
  (53, 'S'): 10,
  (53, 'T'): 10,
  (53, 'U'): 10,
  (53, 'V'): 10,
  (53, 'W'): 10,
  (53, 'X'): 10,
  (53, 'Y'): 10,
  (53, 'Z'): 10,
  (53, '_'): 10,
  (53, 'a'): 10,
  (53, 'b'): 10,
  (53, 'c'): 10,
  (53, 'd'): 10,
  (53, 'e'): 10,
  (53, 'f'): 10,
  (53, 'g'): 10,
  (53, 'h'): 10,
  (53, 'i'): 10,
  (53, 'j'): 10,
  (53, 'k'): 10,
  (53, 'l'): 10,
  (53, 'm'): 10,
  (53, 'n'): 10,
  (53, 'o'): 10,
  (53, 'p'): 10,
  (53, 'q'): 10,
  (53, 'r'): 10,
  (53, 's'): 10,
  (53, 't'): 10,
  (53, 'u'): 10,
  (53, 'v'): 10,
  (53, 'w'): 10,
  (53, 'x'): 10,
  (53, 'y'): 10,
  (53, 'z'): 10,
  (54, '='): 63,
  (55, '.'): 62,
  (56, '='): 61,
  (59, '='): 60,
  (64, '>'): 66,
  (67, '0'): 10,
  (67, '1'): 10,
  (67, '2'): 10,
  (67, '3'): 10,
  (67, '4'): 10,
  (67, '5'): 10,
  (67, '6'): 10,
  (67, '7'): 10,
  (67, '8'): 10,
  (67, '9'): 10,
  (67, 'A'): 10,
  (67, 'B'): 10,
  (67, 'C'): 10,
  (67, 'D'): 10,
  (67, 'E'): 10,
  (67, 'F'): 10,
  (67, 'G'): 10,
  (67, 'H'): 10,
  (67, 'I'): 10,
  (67, 'J'): 10,
  (67, 'K'): 10,
  (67, 'L'): 10,
  (67, 'M'): 10,
  (67, 'N'): 10,
  (67, 'O'): 10,
  (67, 'P'): 10,
  (67, 'Q'): 10,
  (67, 'R'): 10,
  (67, 'S'): 10,
  (67, 'T'): 10,
  (67, 'U'): 10,
  (67, 'V'): 10,
  (67, 'W'): 10,
  (67, 'X'): 10,
  (67, 'Y'): 10,
  (67, 'Z'): 10,
  (67, '_'): 10,
  (67, 'a'): 10,
  (67, 'b'): 10,
  (67, 'c'): 10,
  (67, 'd'): 10,
  (67, 'e'): 10,
  (67, 'f'): 10,
  (67, 'g'): 10,
  (67, 'h'): 10,
  (67, 'i'): 10,
  (67, 'j'): 10,
  (67, 'k'): 10,
  (67, 'l'): 10,
  (67, 'm'): 68,
  (67, 'n'): 10,
  (67, 'o'): 10,
  (67, 'p'): 10,
  (67, 'q'): 10,
  (67, 'r'): 10,
  (67, 's'): 10,
  (67, 't'): 10,
  (67, 'u'): 10,
  (67, 'v'): 10,
  (67, 'w'): 10,
  (67, 'x'): 10,
  (67, 'y'): 10,
  (67, 'z'): 10,
  (68, '0'): 10,
  (68, '1'): 10,
  (68, '2'): 10,
  (68, '3'): 10,
  (68, '4'): 10,
  (68, '5'): 10,
  (68, '6'): 10,
  (68, '7'): 10,
  (68, '8'): 10,
  (68, '9'): 10,
  (68, 'A'): 10,
  (68, 'B'): 10,
  (68, 'C'): 10,
  (68, 'D'): 10,
  (68, 'E'): 10,
  (68, 'F'): 10,
  (68, 'G'): 10,
  (68, 'H'): 10,
  (68, 'I'): 10,
  (68, 'J'): 10,
  (68, 'K'): 10,
  (68, 'L'): 10,
  (68, 'M'): 10,
  (68, 'N'): 10,
  (68, 'O'): 10,
  (68, 'P'): 10,
  (68, 'Q'): 10,
  (68, 'R'): 10,
  (68, 'S'): 10,
  (68, 'T'): 10,
  (68, 'U'): 10,
  (68, 'V'): 10,
  (68, 'W'): 10,
  (68, 'X'): 10,
  (68, 'Y'): 10,
  (68, 'Z'): 10,
  (68, '_'): 10,
  (68, 'a'): 10,
  (68, 'b'): 10,
  (68, 'c'): 10,
  (68, 'd'): 10,
  (68, 'e'): 10,
  (68, 'f'): 10,
  (68, 'g'): 10,
  (68, 'h'): 10,
  (68, 'i'): 10,
  (68, 'j'): 10,
  (68, 'k'): 10,
  (68, 'l'): 10,
  (68, 'm'): 10,
  (68, 'n'): 10,
  (68, 'o'): 10,
  (68, 'p'): 10,
  (68, 'q'): 10,
  (68, 'r'): 10,
  (68, 's'): 10,
  (68, 't'): 10,
  (68, 'u'): 10,
  (68, 'v'): 10,
  (68, 'w'): 10,
  (68, 'x'): 10,
  (68, 'y'): 10,
  (68, 'z'): 10,
  (69, '0'): 10,
  (69, '1'): 10,
  (69, '2'): 10,
  (69, '3'): 10,
  (69, '4'): 10,
  (69, '5'): 10,
  (69, '6'): 10,
  (69, '7'): 10,
  (69, '8'): 10,
  (69, '9'): 10,
  (69, 'A'): 10,
  (69, 'B'): 10,
  (69, 'C'): 10,
  (69, 'D'): 10,
  (69, 'E'): 10,
  (69, 'F'): 10,
  (69, 'G'): 10,
  (69, 'H'): 10,
  (69, 'I'): 10,
  (69, 'J'): 10,
  (69, 'K'): 10,
  (69, 'L'): 10,
  (69, 'M'): 10,
  (69, 'N'): 10,
  (69, 'O'): 10,
  (69, 'P'): 10,
  (69, 'Q'): 10,
  (69, 'R'): 10,
  (69, 'S'): 10,
  (69, 'T'): 10,
  (69, 'U'): 10,
  (69, 'V'): 10,
  (69, 'W'): 10,
  (69, 'X'): 10,
  (69, 'Y'): 10,
  (69, 'Z'): 10,
  (69, '_'): 10,
  (69, 'a'): 10,
  (69, 'b'): 10,
  (69, 'c'): 10,
  (69, 'd'): 10,
  (69, 'e'): 10,
  (69, 'f'): 10,
  (69, 'g'): 10,
  (69, 'h'): 10,
  (69, 'i'): 10,
  (69, 'j'): 10,
  (69, 'k'): 10,
  (69, 'l'): 10,
  (69, 'm'): 10,
  (69, 'n'): 10,
  (69, 'o'): 70,
  (69, 'p'): 10,
  (69, 'q'): 10,
  (69, 'r'): 10,
  (69, 's'): 10,
  (69, 't'): 10,
  (69, 'u'): 10,
  (69, 'v'): 10,
  (69, 'w'): 10,
  (69, 'x'): 10,
  (69, 'y'): 10,
  (69, 'z'): 10,
  (70, '0'): 10,
  (70, '1'): 10,
  (70, '2'): 10,
  (70, '3'): 10,
  (70, '4'): 10,
  (70, '5'): 10,
  (70, '6'): 10,
  (70, '7'): 10,
  (70, '8'): 10,
  (70, '9'): 10,
  (70, 'A'): 10,
  (70, 'B'): 10,
  (70, 'C'): 10,
  (70, 'D'): 10,
  (70, 'E'): 10,
  (70, 'F'): 10,
  (70, 'G'): 10,
  (70, 'H'): 10,
  (70, 'I'): 10,
  (70, 'J'): 10,
  (70, 'K'): 10,
  (70, 'L'): 10,
  (70, 'M'): 10,
  (70, 'N'): 10,
  (70, 'O'): 10,
  (70, 'P'): 10,
  (70, 'Q'): 10,
  (70, 'R'): 10,
  (70, 'S'): 10,
  (70, 'T'): 10,
  (70, 'U'): 10,
  (70, 'V'): 10,
  (70, 'W'): 10,
  (70, 'X'): 10,
  (70, 'Y'): 10,
  (70, 'Z'): 10,
  (70, '_'): 10,
  (70, 'a'): 10,
  (70, 'b'): 10,
  (70, 'c'): 71,
  (70, 'd'): 10,
  (70, 'e'): 10,
  (70, 'f'): 10,
  (70, 'g'): 10,
  (70, 'h'): 10,
  (70, 'i'): 10,
  (70, 'j'): 10,
  (70, 'k'): 10,
  (70, 'l'): 10,
  (70, 'm'): 10,
  (70, 'n'): 10,
  (70, 'o'): 10,
  (70, 'p'): 10,
  (70, 'q'): 10,
  (70, 'r'): 10,
  (70, 's'): 10,
  (70, 't'): 10,
  (70, 'u'): 10,
  (70, 'v'): 10,
  (70, 'w'): 10,
  (70, 'x'): 10,
  (70, 'y'): 10,
  (70, 'z'): 10,
  (71, '0'): 10,
  (71, '1'): 10,
  (71, '2'): 10,
  (71, '3'): 10,
  (71, '4'): 10,
  (71, '5'): 10,
  (71, '6'): 10,
  (71, '7'): 10,
  (71, '8'): 10,
  (71, '9'): 10,
  (71, 'A'): 10,
  (71, 'B'): 10,
  (71, 'C'): 10,
  (71, 'D'): 10,
  (71, 'E'): 10,
  (71, 'F'): 10,
  (71, 'G'): 10,
  (71, 'H'): 10,
  (71, 'I'): 10,
  (71, 'J'): 10,
  (71, 'K'): 10,
  (71, 'L'): 10,
  (71, 'M'): 10,
  (71, 'N'): 10,
  (71, 'O'): 10,
  (71, 'P'): 10,
  (71, 'Q'): 10,
  (71, 'R'): 10,
  (71, 'S'): 10,
  (71, 'T'): 10,
  (71, 'U'): 10,
  (71, 'V'): 10,
  (71, 'W'): 10,
  (71, 'X'): 10,
  (71, 'Y'): 10,
  (71, 'Z'): 10,
  (71, '_'): 10,
  (71, 'a'): 10,
  (71, 'b'): 10,
  (71, 'c'): 10,
  (71, 'd'): 10,
  (71, 'e'): 10,
  (71, 'f'): 10,
  (71, 'g'): 10,
  (71, 'h'): 10,
  (71, 'i'): 10,
  (71, 'j'): 10,
  (71, 'k'): 72,
  (71, 'l'): 10,
  (71, 'm'): 10,
  (71, 'n'): 10,
  (71, 'o'): 10,
  (71, 'p'): 10,
  (71, 'q'): 10,
  (71, 'r'): 10,
  (71, 's'): 10,
  (71, 't'): 10,
  (71, 'u'): 10,
  (71, 'v'): 10,
  (71, 'w'): 10,
  (71, 'x'): 10,
  (71, 'y'): 10,
  (71, 'z'): 10,
  (72, '0'): 10,
  (72, '1'): 10,
  (72, '2'): 10,
  (72, '3'): 10,
  (72, '4'): 10,
  (72, '5'): 10,
  (72, '6'): 10,
  (72, '7'): 10,
  (72, '8'): 10,
  (72, '9'): 10,
  (72, 'A'): 10,
  (72, 'B'): 10,
  (72, 'C'): 10,
  (72, 'D'): 10,
  (72, 'E'): 10,
  (72, 'F'): 10,
  (72, 'G'): 10,
  (72, 'H'): 10,
  (72, 'I'): 10,
  (72, 'J'): 10,
  (72, 'K'): 10,
  (72, 'L'): 10,
  (72, 'M'): 10,
  (72, 'N'): 10,
  (72, 'O'): 10,
  (72, 'P'): 10,
  (72, 'Q'): 10,
  (72, 'R'): 10,
  (72, 'S'): 10,
  (72, 'T'): 10,
  (72, 'U'): 10,
  (72, 'V'): 10,
  (72, 'W'): 10,
  (72, 'X'): 10,
  (72, 'Y'): 10,
  (72, 'Z'): 10,
  (72, '_'): 10,
  (72, 'a'): 10,
  (72, 'b'): 10,
  (72, 'c'): 10,
  (72, 'd'): 10,
  (72, 'e'): 10,
  (72, 'f'): 10,
  (72, 'g'): 10,
  (72, 'h'): 10,
  (72, 'i'): 10,
  (72, 'j'): 10,
  (72, 'k'): 10,
  (72, 'l'): 10,
  (72, 'm'): 10,
  (72, 'n'): 10,
  (72, 'o'): 10,
  (72, 'p'): 10,
  (72, 'q'): 10,
  (72, 'r'): 10,
  (72, 's'): 10,
  (72, 't'): 10,
  (72, 'u'): 10,
  (72, 'v'): 10,
  (72, 'w'): 10,
  (72, 'x'): 10,
  (72, 'y'): 10,
  (72, 'z'): 10,
  (80, '\x00'): 80,
  (80, '\x01'): 80,
  (80, '\x02'): 80,
  (80, '\x03'): 80,
  (80, '\x04'): 80,
  (80, '\x05'): 80,
  (80, '\x06'): 80,
  (80, '\x07'): 80,
  (80, '\x08'): 80,
  (80, '\t'): 80,
  (80, '\n'): 80,
  (80, '\x0b'): 80,
  (80, '\x0c'): 80,
  (80, '\r'): 80,
  (80, '\x0e'): 80,
  (80, '\x0f'): 80,
  (80, '\x10'): 80,
  (80, '\x11'): 80,
  (80, '\x12'): 80,
  (80, '\x13'): 80,
  (80, '\x14'): 80,
  (80, '\x15'): 80,
  (80, '\x16'): 80,
  (80, '\x17'): 80,
  (80, '\x18'): 80,
  (80, '\x19'): 80,
  (80, '\x1a'): 80,
  (80, '\x1b'): 80,
  (80, '\x1c'): 80,
  (80, '\x1d'): 80,
  (80, '\x1e'): 80,
  (80, '\x1f'): 80,
  (80, ' '): 80,
  (80, '!'): 80,
  (80, '"'): 80,
  (80, '#'): 80,
  (80, '$'): 80,
  (80, '%'): 80,
  (80, '&'): 80,
  (80, "'"): 80,
  (80, '('): 80,
  (80, ')'): 80,
  (80, '*'): 83,
  (80, '+'): 80,
  (80, ','): 80,
  (80, '-'): 80,
  (80, '.'): 80,
  (80, '/'): 80,
  (80, '0'): 80,
  (80, '1'): 80,
  (80, '2'): 80,
  (80, '3'): 80,
  (80, '4'): 80,
  (80, '5'): 80,
  (80, '6'): 80,
  (80, '7'): 80,
  (80, '8'): 80,
  (80, '9'): 80,
  (80, ':'): 80,
  (80, ';'): 80,
  (80, '<'): 80,
  (80, '='): 80,
  (80, '>'): 80,
  (80, '?'): 80,
  (80, '@'): 80,
  (80, 'A'): 80,
  (80, 'B'): 80,
  (80, 'C'): 80,
  (80, 'D'): 80,
  (80, 'E'): 80,
  (80, 'F'): 80,
  (80, 'G'): 80,
  (80, 'H'): 80,
  (80, 'I'): 80,
  (80, 'J'): 80,
  (80, 'K'): 80,
  (80, 'L'): 80,
  (80, 'M'): 80,
  (80, 'N'): 80,
  (80, 'O'): 80,
  (80, 'P'): 80,
  (80, 'Q'): 80,
  (80, 'R'): 80,
  (80, 'S'): 80,
  (80, 'T'): 80,
  (80, 'U'): 80,
  (80, 'V'): 80,
  (80, 'W'): 80,
  (80, 'X'): 80,
  (80, 'Y'): 80,
  (80, 'Z'): 80,
  (80, '['): 80,
  (80, '\\'): 80,
  (80, ']'): 80,
  (80, '^'): 80,
  (80, '_'): 80,
  (80, '`'): 80,
  (80, 'a'): 80,
  (80, 'b'): 80,
  (80, 'c'): 80,
  (80, 'd'): 80,
  (80, 'e'): 80,
  (80, 'f'): 80,
  (80, 'g'): 80,
  (80, 'h'): 80,
  (80, 'i'): 80,
  (80, 'j'): 80,
  (80, 'k'): 80,
  (80, 'l'): 80,
  (80, 'm'): 80,
  (80, 'n'): 80,
  (80, 'o'): 80,
  (80, 'p'): 80,
  (80, 'q'): 80,
  (80, 'r'): 80,
  (80, 's'): 80,
  (80, 't'): 80,
  (80, 'u'): 80,
  (80, 'v'): 80,
  (80, 'w'): 80,
  (80, 'x'): 80,
  (80, 'y'): 80,
  (80, 'z'): 80,
  (80, '{'): 80,
  (80, '|'): 80,
  (80, '}'): 80,
  (80, '~'): 80,
  (80, '\x7f'): 80,
  (80, '\x80'): 80,
  (80, '\x81'): 80,
  (80, '\x82'): 80,
  (80, '\x83'): 80,
  (80, '\x84'): 80,
  (80, '\x85'): 80,
  (80, '\x86'): 80,
  (80, '\x87'): 80,
  (80, '\x88'): 80,
  (80, '\x89'): 80,
  (80, '\x8a'): 80,
  (80, '\x8b'): 80,
  (80, '\x8c'): 80,
  (80, '\x8d'): 80,
  (80, '\x8e'): 80,
  (80, '\x8f'): 80,
  (80, '\x90'): 80,
  (80, '\x91'): 80,
  (80, '\x92'): 80,
  (80, '\x93'): 80,
  (80, '\x94'): 80,
  (80, '\x95'): 80,
  (80, '\x96'): 80,
  (80, '\x97'): 80,
  (80, '\x98'): 80,
  (80, '\x99'): 80,
  (80, '\x9a'): 80,
  (80, '\x9b'): 80,
  (80, '\x9c'): 80,
  (80, '\x9d'): 80,
  (80, '\x9e'): 80,
  (80, '\x9f'): 80,
  (80, '\xa0'): 80,
  (80, '\xa1'): 80,
  (80, '\xa2'): 80,
  (80, '\xa3'): 80,
  (80, '\xa4'): 80,
  (80, '\xa5'): 80,
  (80, '\xa6'): 80,
  (80, '\xa7'): 80,
  (80, '\xa8'): 80,
  (80, '\xa9'): 80,
  (80, '\xaa'): 80,
  (80, '\xab'): 80,
  (80, '\xac'): 80,
  (80, '\xad'): 80,
  (80, '\xae'): 80,
  (80, '\xaf'): 80,
  (80, '\xb0'): 80,
  (80, '\xb1'): 80,
  (80, '\xb2'): 80,
  (80, '\xb3'): 80,
  (80, '\xb4'): 80,
  (80, '\xb5'): 80,
  (80, '\xb6'): 80,
  (80, '\xb7'): 80,
  (80, '\xb8'): 80,
  (80, '\xb9'): 80,
  (80, '\xba'): 80,
  (80, '\xbb'): 80,
  (80, '\xbc'): 80,
  (80, '\xbd'): 80,
  (80, '\xbe'): 80,
  (80, '\xbf'): 80,
  (80, '\xc0'): 80,
  (80, '\xc1'): 80,
  (80, '\xc2'): 80,
  (80, '\xc3'): 80,
  (80, '\xc4'): 80,
  (80, '\xc5'): 80,
  (80, '\xc6'): 80,
  (80, '\xc7'): 80,
  (80, '\xc8'): 80,
  (80, '\xc9'): 80,
  (80, '\xca'): 80,
  (80, '\xcb'): 80,
  (80, '\xcc'): 80,
  (80, '\xcd'): 80,
  (80, '\xce'): 80,
  (80, '\xcf'): 80,
  (80, '\xd0'): 80,
  (80, '\xd1'): 80,
  (80, '\xd2'): 80,
  (80, '\xd3'): 80,
  (80, '\xd4'): 80,
  (80, '\xd5'): 80,
  (80, '\xd6'): 80,
  (80, '\xd7'): 80,
  (80, '\xd8'): 80,
  (80, '\xd9'): 80,
  (80, '\xda'): 80,
  (80, '\xdb'): 80,
  (80, '\xdc'): 80,
  (80, '\xdd'): 80,
  (80, '\xde'): 80,
  (80, '\xdf'): 80,
  (80, '\xe0'): 80,
  (80, '\xe1'): 80,
  (80, '\xe2'): 80,
  (80, '\xe3'): 80,
  (80, '\xe4'): 80,
  (80, '\xe5'): 80,
  (80, '\xe6'): 80,
  (80, '\xe7'): 80,
  (80, '\xe8'): 80,
  (80, '\xe9'): 80,
  (80, '\xea'): 80,
  (80, '\xeb'): 80,
  (80, '\xec'): 80,
  (80, '\xed'): 80,
  (80, '\xee'): 80,
  (80, '\xef'): 80,
  (80, '\xf0'): 80,
  (80, '\xf1'): 80,
  (80, '\xf2'): 80,
  (80, '\xf3'): 80,
  (80, '\xf4'): 80,
  (80, '\xf5'): 80,
  (80, '\xf6'): 80,
  (80, '\xf7'): 80,
  (80, '\xf8'): 80,
  (80, '\xf9'): 80,
  (80, '\xfa'): 80,
  (80, '\xfb'): 80,
  (80, '\xfc'): 80,
  (80, '\xfd'): 80,
  (80, '\xfe'): 80,
  (80, '\xff'): 80,
  (83, '\x00'): 80,
  (83, '\x01'): 80,
  (83, '\x02'): 80,
  (83, '\x03'): 80,
  (83, '\x04'): 80,
  (83, '\x05'): 80,
  (83, '\x06'): 80,
  (83, '\x07'): 80,
  (83, '\x08'): 80,
  (83, '\t'): 80,
  (83, '\n'): 80,
  (83, '\x0b'): 80,
  (83, '\x0c'): 80,
  (83, '\r'): 80,
  (83, '\x0e'): 80,
  (83, '\x0f'): 80,
  (83, '\x10'): 80,
  (83, '\x11'): 80,
  (83, '\x12'): 80,
  (83, '\x13'): 80,
  (83, '\x14'): 80,
  (83, '\x15'): 80,
  (83, '\x16'): 80,
  (83, '\x17'): 80,
  (83, '\x18'): 80,
  (83, '\x19'): 80,
  (83, '\x1a'): 80,
  (83, '\x1b'): 80,
  (83, '\x1c'): 80,
  (83, '\x1d'): 80,
  (83, '\x1e'): 80,
  (83, '\x1f'): 80,
  (83, ' '): 80,
  (83, '!'): 80,
  (83, '"'): 80,
  (83, '#'): 80,
  (83, '$'): 80,
  (83, '%'): 80,
  (83, '&'): 80,
  (83, "'"): 80,
  (83, '('): 80,
  (83, ')'): 80,
  (83, '*'): 84,
  (83, '+'): 80,
  (83, ','): 80,
  (83, '-'): 80,
  (83, '.'): 80,
  (83, '/'): 1,
  (83, '0'): 80,
  (83, '1'): 80,
  (83, '2'): 80,
  (83, '3'): 80,
  (83, '4'): 80,
  (83, '5'): 80,
  (83, '6'): 80,
  (83, '7'): 80,
  (83, '8'): 80,
  (83, '9'): 80,
  (83, ':'): 80,
  (83, ';'): 80,
  (83, '<'): 80,
  (83, '='): 80,
  (83, '>'): 80,
  (83, '?'): 80,
  (83, '@'): 80,
  (83, 'A'): 80,
  (83, 'B'): 80,
  (83, 'C'): 80,
  (83, 'D'): 80,
  (83, 'E'): 80,
  (83, 'F'): 80,
  (83, 'G'): 80,
  (83, 'H'): 80,
  (83, 'I'): 80,
  (83, 'J'): 80,
  (83, 'K'): 80,
  (83, 'L'): 80,
  (83, 'M'): 80,
  (83, 'N'): 80,
  (83, 'O'): 80,
  (83, 'P'): 80,
  (83, 'Q'): 80,
  (83, 'R'): 80,
  (83, 'S'): 80,
  (83, 'T'): 80,
  (83, 'U'): 80,
  (83, 'V'): 80,
  (83, 'W'): 80,
  (83, 'X'): 80,
  (83, 'Y'): 80,
  (83, 'Z'): 80,
  (83, '['): 80,
  (83, '\\'): 80,
  (83, ']'): 80,
  (83, '^'): 80,
  (83, '_'): 80,
  (83, '`'): 80,
  (83, 'a'): 80,
  (83, 'b'): 80,
  (83, 'c'): 80,
  (83, 'd'): 80,
  (83, 'e'): 80,
  (83, 'f'): 80,
  (83, 'g'): 80,
  (83, 'h'): 80,
  (83, 'i'): 80,
  (83, 'j'): 80,
  (83, 'k'): 80,
  (83, 'l'): 80,
  (83, 'm'): 80,
  (83, 'n'): 80,
  (83, 'o'): 80,
  (83, 'p'): 80,
  (83, 'q'): 80,
  (83, 'r'): 80,
  (83, 's'): 80,
  (83, 't'): 80,
  (83, 'u'): 80,
  (83, 'v'): 80,
  (83, 'w'): 80,
  (83, 'x'): 80,
  (83, 'y'): 80,
  (83, 'z'): 80,
  (83, '{'): 80,
  (83, '|'): 80,
  (83, '}'): 80,
  (83, '~'): 80,
  (83, '\x7f'): 80,
  (83, '\x80'): 80,
  (83, '\x81'): 80,
  (83, '\x82'): 80,
  (83, '\x83'): 80,
  (83, '\x84'): 80,
  (83, '\x85'): 80,
  (83, '\x86'): 80,
  (83, '\x87'): 80,
  (83, '\x88'): 80,
  (83, '\x89'): 80,
  (83, '\x8a'): 80,
  (83, '\x8b'): 80,
  (83, '\x8c'): 80,
  (83, '\x8d'): 80,
  (83, '\x8e'): 80,
  (83, '\x8f'): 80,
  (83, '\x90'): 80,
  (83, '\x91'): 80,
  (83, '\x92'): 80,
  (83, '\x93'): 80,
  (83, '\x94'): 80,
  (83, '\x95'): 80,
  (83, '\x96'): 80,
  (83, '\x97'): 80,
  (83, '\x98'): 80,
  (83, '\x99'): 80,
  (83, '\x9a'): 80,
  (83, '\x9b'): 80,
  (83, '\x9c'): 80,
  (83, '\x9d'): 80,
  (83, '\x9e'): 80,
  (83, '\x9f'): 80,
  (83, '\xa0'): 80,
  (83, '\xa1'): 80,
  (83, '\xa2'): 80,
  (83, '\xa3'): 80,
  (83, '\xa4'): 80,
  (83, '\xa5'): 80,
  (83, '\xa6'): 80,
  (83, '\xa7'): 80,
  (83, '\xa8'): 80,
  (83, '\xa9'): 80,
  (83, '\xaa'): 80,
  (83, '\xab'): 80,
  (83, '\xac'): 80,
  (83, '\xad'): 80,
  (83, '\xae'): 80,
  (83, '\xaf'): 80,
  (83, '\xb0'): 80,
  (83, '\xb1'): 80,
  (83, '\xb2'): 80,
  (83, '\xb3'): 80,
  (83, '\xb4'): 80,
  (83, '\xb5'): 80,
  (83, '\xb6'): 80,
  (83, '\xb7'): 80,
  (83, '\xb8'): 80,
  (83, '\xb9'): 80,
  (83, '\xba'): 80,
  (83, '\xbb'): 80,
  (83, '\xbc'): 80,
  (83, '\xbd'): 80,
  (83, '\xbe'): 80,
  (83, '\xbf'): 80,
  (83, '\xc0'): 80,
  (83, '\xc1'): 80,
  (83, '\xc2'): 80,
  (83, '\xc3'): 80,
  (83, '\xc4'): 80,
  (83, '\xc5'): 80,
  (83, '\xc6'): 80,
  (83, '\xc7'): 80,
  (83, '\xc8'): 80,
  (83, '\xc9'): 80,
  (83, '\xca'): 80,
  (83, '\xcb'): 80,
  (83, '\xcc'): 80,
  (83, '\xcd'): 80,
  (83, '\xce'): 80,
  (83, '\xcf'): 80,
  (83, '\xd0'): 80,
  (83, '\xd1'): 80,
  (83, '\xd2'): 80,
  (83, '\xd3'): 80,
  (83, '\xd4'): 80,
  (83, '\xd5'): 80,
  (83, '\xd6'): 80,
  (83, '\xd7'): 80,
  (83, '\xd8'): 80,
  (83, '\xd9'): 80,
  (83, '\xda'): 80,
  (83, '\xdb'): 80,
  (83, '\xdc'): 80,
  (83, '\xdd'): 80,
  (83, '\xde'): 80,
  (83, '\xdf'): 80,
  (83, '\xe0'): 80,
  (83, '\xe1'): 80,
  (83, '\xe2'): 80,
  (83, '\xe3'): 80,
  (83, '\xe4'): 80,
  (83, '\xe5'): 80,
  (83, '\xe6'): 80,
  (83, '\xe7'): 80,
  (83, '\xe8'): 80,
  (83, '\xe9'): 80,
  (83, '\xea'): 80,
  (83, '\xeb'): 80,
  (83, '\xec'): 80,
  (83, '\xed'): 80,
  (83, '\xee'): 80,
  (83, '\xef'): 80,
  (83, '\xf0'): 80,
  (83, '\xf1'): 80,
  (83, '\xf2'): 80,
  (83, '\xf3'): 80,
  (83, '\xf4'): 80,
  (83, '\xf5'): 80,
  (83, '\xf6'): 80,
  (83, '\xf7'): 80,
  (83, '\xf8'): 80,
  (83, '\xf9'): 80,
  (83, '\xfa'): 80,
  (83, '\xfb'): 80,
  (83, '\xfc'): 80,
  (83, '\xfd'): 80,
  (83, '\xfe'): 80,
  (83, '\xff'): 80,
  (84, '\x00'): 80,
  (84, '\x01'): 80,
  (84, '\x02'): 80,
  (84, '\x03'): 80,
  (84, '\x04'): 80,
  (84, '\x05'): 80,
  (84, '\x06'): 80,
  (84, '\x07'): 80,
  (84, '\x08'): 80,
  (84, '\t'): 80,
  (84, '\n'): 80,
  (84, '\x0b'): 80,
  (84, '\x0c'): 80,
  (84, '\r'): 80,
  (84, '\x0e'): 80,
  (84, '\x0f'): 80,
  (84, '\x10'): 80,
  (84, '\x11'): 80,
  (84, '\x12'): 80,
  (84, '\x13'): 80,
  (84, '\x14'): 80,
  (84, '\x15'): 80,
  (84, '\x16'): 80,
  (84, '\x17'): 80,
  (84, '\x18'): 80,
  (84, '\x19'): 80,
  (84, '\x1a'): 80,
  (84, '\x1b'): 80,
  (84, '\x1c'): 80,
  (84, '\x1d'): 80,
  (84, '\x1e'): 80,
  (84, '\x1f'): 80,
  (84, ' '): 80,
  (84, '!'): 80,
  (84, '"'): 80,
  (84, '#'): 80,
  (84, '$'): 80,
  (84, '%'): 80,
  (84, '&'): 80,
  (84, "'"): 80,
  (84, '('): 80,
  (84, ')'): 80,
  (84, '*'): 83,
  (84, '+'): 80,
  (84, ','): 80,
  (84, '-'): 80,
  (84, '.'): 80,
  (84, '/'): 85,
  (84, '0'): 80,
  (84, '1'): 80,
  (84, '2'): 80,
  (84, '3'): 80,
  (84, '4'): 80,
  (84, '5'): 80,
  (84, '6'): 80,
  (84, '7'): 80,
  (84, '8'): 80,
  (84, '9'): 80,
  (84, ':'): 80,
  (84, ';'): 80,
  (84, '<'): 80,
  (84, '='): 80,
  (84, '>'): 80,
  (84, '?'): 80,
  (84, '@'): 80,
  (84, 'A'): 80,
  (84, 'B'): 80,
  (84, 'C'): 80,
  (84, 'D'): 80,
  (84, 'E'): 80,
  (84, 'F'): 80,
  (84, 'G'): 80,
  (84, 'H'): 80,
  (84, 'I'): 80,
  (84, 'J'): 80,
  (84, 'K'): 80,
  (84, 'L'): 80,
  (84, 'M'): 80,
  (84, 'N'): 80,
  (84, 'O'): 80,
  (84, 'P'): 80,
  (84, 'Q'): 80,
  (84, 'R'): 80,
  (84, 'S'): 80,
  (84, 'T'): 80,
  (84, 'U'): 80,
  (84, 'V'): 80,
  (84, 'W'): 80,
  (84, 'X'): 80,
  (84, 'Y'): 80,
  (84, 'Z'): 80,
  (84, '['): 80,
  (84, '\\'): 80,
  (84, ']'): 80,
  (84, '^'): 80,
  (84, '_'): 80,
  (84, '`'): 80,
  (84, 'a'): 80,
  (84, 'b'): 80,
  (84, 'c'): 80,
  (84, 'd'): 80,
  (84, 'e'): 80,
  (84, 'f'): 80,
  (84, 'g'): 80,
  (84, 'h'): 80,
  (84, 'i'): 80,
  (84, 'j'): 80,
  (84, 'k'): 80,
  (84, 'l'): 80,
  (84, 'm'): 80,
  (84, 'n'): 80,
  (84, 'o'): 80,
  (84, 'p'): 80,
  (84, 'q'): 80,
  (84, 'r'): 80,
  (84, 's'): 80,
  (84, 't'): 80,
  (84, 'u'): 80,
  (84, 'v'): 80,
  (84, 'w'): 80,
  (84, 'x'): 80,
  (84, 'y'): 80,
  (84, 'z'): 80,
  (84, '{'): 80,
  (84, '|'): 80,
  (84, '}'): 80,
  (84, '~'): 80,
  (84, '\x7f'): 80,
  (84, '\x80'): 80,
  (84, '\x81'): 80,
  (84, '\x82'): 80,
  (84, '\x83'): 80,
  (84, '\x84'): 80,
  (84, '\x85'): 80,
  (84, '\x86'): 80,
  (84, '\x87'): 80,
  (84, '\x88'): 80,
  (84, '\x89'): 80,
  (84, '\x8a'): 80,
  (84, '\x8b'): 80,
  (84, '\x8c'): 80,
  (84, '\x8d'): 80,
  (84, '\x8e'): 80,
  (84, '\x8f'): 80,
  (84, '\x90'): 80,
  (84, '\x91'): 80,
  (84, '\x92'): 80,
  (84, '\x93'): 80,
  (84, '\x94'): 80,
  (84, '\x95'): 80,
  (84, '\x96'): 80,
  (84, '\x97'): 80,
  (84, '\x98'): 80,
  (84, '\x99'): 80,
  (84, '\x9a'): 80,
  (84, '\x9b'): 80,
  (84, '\x9c'): 80,
  (84, '\x9d'): 80,
  (84, '\x9e'): 80,
  (84, '\x9f'): 80,
  (84, '\xa0'): 80,
  (84, '\xa1'): 80,
  (84, '\xa2'): 80,
  (84, '\xa3'): 80,
  (84, '\xa4'): 80,
  (84, '\xa5'): 80,
  (84, '\xa6'): 80,
  (84, '\xa7'): 80,
  (84, '\xa8'): 80,
  (84, '\xa9'): 80,
  (84, '\xaa'): 80,
  (84, '\xab'): 80,
  (84, '\xac'): 80,
  (84, '\xad'): 80,
  (84, '\xae'): 80,
  (84, '\xaf'): 80,
  (84, '\xb0'): 80,
  (84, '\xb1'): 80,
  (84, '\xb2'): 80,
  (84, '\xb3'): 80,
  (84, '\xb4'): 80,
  (84, '\xb5'): 80,
  (84, '\xb6'): 80,
  (84, '\xb7'): 80,
  (84, '\xb8'): 80,
  (84, '\xb9'): 80,
  (84, '\xba'): 80,
  (84, '\xbb'): 80,
  (84, '\xbc'): 80,
  (84, '\xbd'): 80,
  (84, '\xbe'): 80,
  (84, '\xbf'): 80,
  (84, '\xc0'): 80,
  (84, '\xc1'): 80,
  (84, '\xc2'): 80,
  (84, '\xc3'): 80,
  (84, '\xc4'): 80,
  (84, '\xc5'): 80,
  (84, '\xc6'): 80,
  (84, '\xc7'): 80,
  (84, '\xc8'): 80,
  (84, '\xc9'): 80,
  (84, '\xca'): 80,
  (84, '\xcb'): 80,
  (84, '\xcc'): 80,
  (84, '\xcd'): 80,
  (84, '\xce'): 80,
  (84, '\xcf'): 80,
  (84, '\xd0'): 80,
  (84, '\xd1'): 80,
  (84, '\xd2'): 80,
  (84, '\xd3'): 80,
  (84, '\xd4'): 80,
  (84, '\xd5'): 80,
  (84, '\xd6'): 80,
  (84, '\xd7'): 80,
  (84, '\xd8'): 80,
  (84, '\xd9'): 80,
  (84, '\xda'): 80,
  (84, '\xdb'): 80,
  (84, '\xdc'): 80,
  (84, '\xdd'): 80,
  (84, '\xde'): 80,
  (84, '\xdf'): 80,
  (84, '\xe0'): 80,
  (84, '\xe1'): 80,
  (84, '\xe2'): 80,
  (84, '\xe3'): 80,
  (84, '\xe4'): 80,
  (84, '\xe5'): 80,
  (84, '\xe6'): 80,
  (84, '\xe7'): 80,
  (84, '\xe8'): 80,
  (84, '\xe9'): 80,
  (84, '\xea'): 80,
  (84, '\xeb'): 80,
  (84, '\xec'): 80,
  (84, '\xed'): 80,
  (84, '\xee'): 80,
  (84, '\xef'): 80,
  (84, '\xf0'): 80,
  (84, '\xf1'): 80,
  (84, '\xf2'): 80,
  (84, '\xf3'): 80,
  (84, '\xf4'): 80,
  (84, '\xf5'): 80,
  (84, '\xf6'): 80,
  (84, '\xf7'): 80,
  (84, '\xf8'): 80,
  (84, '\xf9'): 80,
  (84, '\xfa'): 80,
  (84, '\xfb'): 80,
  (84, '\xfc'): 80,
  (84, '\xfd'): 80,
  (84, '\xfe'): 80,
  (84, '\xff'): 80,
  (85, '\x00'): 80,
  (85, '\x01'): 80,
  (85, '\x02'): 80,
  (85, '\x03'): 80,
  (85, '\x04'): 80,
  (85, '\x05'): 80,
  (85, '\x06'): 80,
  (85, '\x07'): 80,
  (85, '\x08'): 80,
  (85, '\t'): 80,
  (85, '\n'): 80,
  (85, '\x0b'): 80,
  (85, '\x0c'): 80,
  (85, '\r'): 80,
  (85, '\x0e'): 80,
  (85, '\x0f'): 80,
  (85, '\x10'): 80,
  (85, '\x11'): 80,
  (85, '\x12'): 80,
  (85, '\x13'): 80,
  (85, '\x14'): 80,
  (85, '\x15'): 80,
  (85, '\x16'): 80,
  (85, '\x17'): 80,
  (85, '\x18'): 80,
  (85, '\x19'): 80,
  (85, '\x1a'): 80,
  (85, '\x1b'): 80,
  (85, '\x1c'): 80,
  (85, '\x1d'): 80,
  (85, '\x1e'): 80,
  (85, '\x1f'): 80,
  (85, ' '): 80,
  (85, '!'): 80,
  (85, '"'): 80,
  (85, '#'): 80,
  (85, '$'): 80,
  (85, '%'): 80,
  (85, '&'): 80,
  (85, "'"): 80,
  (85, '('): 80,
  (85, ')'): 80,
  (85, '*'): 83,
  (85, '+'): 80,
  (85, ','): 80,
  (85, '-'): 80,
  (85, '.'): 80,
  (85, '/'): 80,
  (85, '0'): 80,
  (85, '1'): 80,
  (85, '2'): 80,
  (85, '3'): 80,
  (85, '4'): 80,
  (85, '5'): 80,
  (85, '6'): 80,
  (85, '7'): 80,
  (85, '8'): 80,
  (85, '9'): 80,
  (85, ':'): 80,
  (85, ';'): 80,
  (85, '<'): 80,
  (85, '='): 80,
  (85, '>'): 80,
  (85, '?'): 80,
  (85, '@'): 80,
  (85, 'A'): 80,
  (85, 'B'): 80,
  (85, 'C'): 80,
  (85, 'D'): 80,
  (85, 'E'): 80,
  (85, 'F'): 80,
  (85, 'G'): 80,
  (85, 'H'): 80,
  (85, 'I'): 80,
  (85, 'J'): 80,
  (85, 'K'): 80,
  (85, 'L'): 80,
  (85, 'M'): 80,
  (85, 'N'): 80,
  (85, 'O'): 80,
  (85, 'P'): 80,
  (85, 'Q'): 80,
  (85, 'R'): 80,
  (85, 'S'): 80,
  (85, 'T'): 80,
  (85, 'U'): 80,
  (85, 'V'): 80,
  (85, 'W'): 80,
  (85, 'X'): 80,
  (85, 'Y'): 80,
  (85, 'Z'): 80,
  (85, '['): 80,
  (85, '\\'): 80,
  (85, ']'): 80,
  (85, '^'): 80,
  (85, '_'): 80,
  (85, '`'): 80,
  (85, 'a'): 80,
  (85, 'b'): 80,
  (85, 'c'): 80,
  (85, 'd'): 80,
  (85, 'e'): 80,
  (85, 'f'): 80,
  (85, 'g'): 80,
  (85, 'h'): 80,
  (85, 'i'): 80,
  (85, 'j'): 80,
  (85, 'k'): 80,
  (85, 'l'): 80,
  (85, 'm'): 80,
  (85, 'n'): 80,
  (85, 'o'): 80,
  (85, 'p'): 80,
  (85, 'q'): 80,
  (85, 'r'): 80,
  (85, 's'): 80,
  (85, 't'): 80,
  (85, 'u'): 80,
  (85, 'v'): 80,
  (85, 'w'): 80,
  (85, 'x'): 80,
  (85, 'y'): 80,
  (85, 'z'): 80,
  (85, '{'): 80,
  (85, '|'): 80,
  (85, '}'): 80,
  (85, '~'): 80,
  (85, '\x7f'): 80,
  (85, '\x80'): 80,
  (85, '\x81'): 80,
  (85, '\x82'): 80,
  (85, '\x83'): 80,
  (85, '\x84'): 80,
  (85, '\x85'): 80,
  (85, '\x86'): 80,
  (85, '\x87'): 80,
  (85, '\x88'): 80,
  (85, '\x89'): 80,
  (85, '\x8a'): 80,
  (85, '\x8b'): 80,
  (85, '\x8c'): 80,
  (85, '\x8d'): 80,
  (85, '\x8e'): 80,
  (85, '\x8f'): 80,
  (85, '\x90'): 80,
  (85, '\x91'): 80,
  (85, '\x92'): 80,
  (85, '\x93'): 80,
  (85, '\x94'): 80,
  (85, '\x95'): 80,
  (85, '\x96'): 80,
  (85, '\x97'): 80,
  (85, '\x98'): 80,
  (85, '\x99'): 80,
  (85, '\x9a'): 80,
  (85, '\x9b'): 80,
  (85, '\x9c'): 80,
  (85, '\x9d'): 80,
  (85, '\x9e'): 80,
  (85, '\x9f'): 80,
  (85, '\xa0'): 80,
  (85, '\xa1'): 80,
  (85, '\xa2'): 80,
  (85, '\xa3'): 80,
  (85, '\xa4'): 80,
  (85, '\xa5'): 80,
  (85, '\xa6'): 80,
  (85, '\xa7'): 80,
  (85, '\xa8'): 80,
  (85, '\xa9'): 80,
  (85, '\xaa'): 80,
  (85, '\xab'): 80,
  (85, '\xac'): 80,
  (85, '\xad'): 80,
  (85, '\xae'): 80,
  (85, '\xaf'): 80,
  (85, '\xb0'): 80,
  (85, '\xb1'): 80,
  (85, '\xb2'): 80,
  (85, '\xb3'): 80,
  (85, '\xb4'): 80,
  (85, '\xb5'): 80,
  (85, '\xb6'): 80,
  (85, '\xb7'): 80,
  (85, '\xb8'): 80,
  (85, '\xb9'): 80,
  (85, '\xba'): 80,
  (85, '\xbb'): 80,
  (85, '\xbc'): 80,
  (85, '\xbd'): 80,
  (85, '\xbe'): 80,
  (85, '\xbf'): 80,
  (85, '\xc0'): 80,
  (85, '\xc1'): 80,
  (85, '\xc2'): 80,
  (85, '\xc3'): 80,
  (85, '\xc4'): 80,
  (85, '\xc5'): 80,
  (85, '\xc6'): 80,
  (85, '\xc7'): 80,
  (85, '\xc8'): 80,
  (85, '\xc9'): 80,
  (85, '\xca'): 80,
  (85, '\xcb'): 80,
  (85, '\xcc'): 80,
  (85, '\xcd'): 80,
  (85, '\xce'): 80,
  (85, '\xcf'): 80,
  (85, '\xd0'): 80,
  (85, '\xd1'): 80,
  (85, '\xd2'): 80,
  (85, '\xd3'): 80,
  (85, '\xd4'): 80,
  (85, '\xd5'): 80,
  (85, '\xd6'): 80,
  (85, '\xd7'): 80,
  (85, '\xd8'): 80,
  (85, '\xd9'): 80,
  (85, '\xda'): 80,
  (85, '\xdb'): 80,
  (85, '\xdc'): 80,
  (85, '\xdd'): 80,
  (85, '\xde'): 80,
  (85, '\xdf'): 80,
  (85, '\xe0'): 80,
  (85, '\xe1'): 80,
  (85, '\xe2'): 80,
  (85, '\xe3'): 80,
  (85, '\xe4'): 80,
  (85, '\xe5'): 80,
  (85, '\xe6'): 80,
  (85, '\xe7'): 80,
  (85, '\xe8'): 80,
  (85, '\xe9'): 80,
  (85, '\xea'): 80,
  (85, '\xeb'): 80,
  (85, '\xec'): 80,
  (85, '\xed'): 80,
  (85, '\xee'): 80,
  (85, '\xef'): 80,
  (85, '\xf0'): 80,
  (85, '\xf1'): 80,
  (85, '\xf2'): 80,
  (85, '\xf3'): 80,
  (85, '\xf4'): 80,
  (85, '\xf5'): 80,
  (85, '\xf6'): 80,
  (85, '\xf7'): 80,
  (85, '\xf8'): 80,
  (85, '\xf9'): 80,
  (85, '\xfa'): 80,
  (85, '\xfb'): 80,
  (85, '\xfc'): 80,
  (85, '\xfd'): 80,
  (85, '\xfe'): 80,
  (85, '\xff'): 80,
  (86, '0'): 10,
  (86, '1'): 10,
  (86, '2'): 10,
  (86, '3'): 10,
  (86, '4'): 10,
  (86, '5'): 10,
  (86, '6'): 10,
  (86, '7'): 10,
  (86, '8'): 10,
  (86, '9'): 10,
  (86, 'A'): 10,
  (86, 'B'): 10,
  (86, 'C'): 10,
  (86, 'D'): 10,
  (86, 'E'): 10,
  (86, 'F'): 10,
  (86, 'G'): 10,
  (86, 'H'): 10,
  (86, 'I'): 10,
  (86, 'J'): 10,
  (86, 'K'): 10,
  (86, 'L'): 10,
  (86, 'M'): 10,
  (86, 'N'): 10,
  (86, 'O'): 10,
  (86, 'P'): 10,
  (86, 'Q'): 10,
  (86, 'R'): 10,
  (86, 'S'): 10,
  (86, 'T'): 10,
  (86, 'U'): 10,
  (86, 'V'): 10,
  (86, 'W'): 10,
  (86, 'X'): 10,
  (86, 'Y'): 10,
  (86, 'Z'): 10,
  (86, '_'): 10,
  (86, 'a'): 10,
  (86, 'b'): 10,
  (86, 'c'): 10,
  (86, 'd'): 10,
  (86, 'e'): 10,
  (86, 'f'): 10,
  (86, 'g'): 10,
  (86, 'h'): 10,
  (86, 'i'): 10,
  (86, 'j'): 10,
  (86, 'k'): 10,
  (86, 'l'): 10,
  (86, 'm'): 10,
  (86, 'n'): 10,
  (86, 'o'): 10,
  (86, 'p'): 10,
  (86, 'q'): 10,
  (86, 'r'): 87,
  (86, 's'): 10,
  (86, 't'): 10,
  (86, 'u'): 10,
  (86, 'v'): 10,
  (86, 'w'): 10,
  (86, 'x'): 10,
  (86, 'y'): 10,
  (86, 'z'): 10,
  (87, '0'): 10,
  (87, '1'): 10,
  (87, '2'): 10,
  (87, '3'): 10,
  (87, '4'): 10,
  (87, '5'): 10,
  (87, '6'): 10,
  (87, '7'): 10,
  (87, '8'): 10,
  (87, '9'): 10,
  (87, 'A'): 10,
  (87, 'B'): 10,
  (87, 'C'): 10,
  (87, 'D'): 10,
  (87, 'E'): 10,
  (87, 'F'): 10,
  (87, 'G'): 10,
  (87, 'H'): 10,
  (87, 'I'): 10,
  (87, 'J'): 10,
  (87, 'K'): 10,
  (87, 'L'): 10,
  (87, 'M'): 10,
  (87, 'N'): 10,
  (87, 'O'): 10,
  (87, 'P'): 10,
  (87, 'Q'): 10,
  (87, 'R'): 10,
  (87, 'S'): 10,
  (87, 'T'): 10,
  (87, 'U'): 10,
  (87, 'V'): 10,
  (87, 'W'): 10,
  (87, 'X'): 10,
  (87, 'Y'): 10,
  (87, 'Z'): 10,
  (87, '_'): 10,
  (87, 'a'): 10,
  (87, 'b'): 10,
  (87, 'c'): 10,
  (87, 'd'): 10,
  (87, 'e'): 10,
  (87, 'f'): 10,
  (87, 'g'): 10,
  (87, 'h'): 10,
  (87, 'i'): 10,
  (87, 'j'): 10,
  (87, 'k'): 10,
  (87, 'l'): 10,
  (87, 'm'): 10,
  (87, 'n'): 10,
  (87, 'o'): 10,
  (87, 'p'): 10,
  (87, 'q'): 10,
  (87, 'r'): 10,
  (87, 's'): 10,
  (87, 't'): 10,
  (87, 'u'): 10,
  (87, 'v'): 10,
  (87, 'w'): 10,
  (87, 'x'): 10,
  (87, 'y'): 10,
  (87, 'z'): 10,
  (89, '='): 91,
  (92, '<'): 96,
  (94, '='): 95,
  (98, '0'): 99,
  (98, '1'): 99,
  (98, '2'): 99,
  (98, '3'): 99,
  (98, '4'): 99,
  (98, '5'): 99,
  (98, '6'): 99,
  (98, '7'): 99,
  (98, '8'): 99,
  (98, '9'): 99,
  (99, '0'): 99,
  (99, '1'): 99,
  (99, '2'): 99,
  (99, '3'): 99,
  (99, '4'): 99,
  (99, '5'): 99,
  (99, '6'): 99,
  (99, '7'): 99,
  (99, '8'): 99,
  (99, '9'): 99},
 set([1,
      2,
      3,
      4,
      5,
      6,
      8,
      9,
      10,
      11,
      12,
      14,
      15,
      16,
      17,
      18,
      19,
      21,
      22,
      23,
      24,
      25,
      26,
      27,
      28,
      29,
      30,
      31,
      32,
      33,
      34,
      35,
      36,
      37,
      38,
      39,
      40,
      41,
      42,
      43,
      44,
      45,
      46,
      47,
      48,
      49,
      50,
      51,
      52,
      53,
      57,
      58,
      60,
      61,
      62,
      63,
      65,
      66,
      67,
      68,
      69,
      70,
      71,
      72,
      73,
      74,
      75,
      76,
      77,
      78,
      79,
      81,
      82,
      85,
      86,
      87,
      88,
      89,
      90,
      91,
      93,
      94,
      95,
      96,
      97,
      99]),
 set([1,
      2,
      3,
      4,
      5,
      6,
      8,
      9,
      10,
      11,
      12,
      14,
      15,
      16,
      17,
      18,
      19,
      21,
      22,
      23,
      24,
      25,
      26,
      27,
      28,
      29,
      30,
      31,
      32,
      33,
      34,
      35,
      36,
      37,
      38,
      39,
      40,
      41,
      42,
      43,
      44,
      45,
      46,
      47,
      48,
      49,
      50,
      51,
      52,
      53,
      57,
      58,
      60,
      61,
      62,
      63,
      65,
      66,
      67,
      68,
      69,
      70,
      71,
      72,
      73,
      74,
      75,
      76,
      77,
      78,
      79,
      81,
      82,
      85,
      86,
      87,
      88,
      89,
      90,
      91,
      93,
      94,
      95,
      96,
      97,
      99]),
 ['0, 0, 0, 0, start|, 0, start|, 0, 0, 0, 0, start|, 0, 0, 0, 0, 0, start|, 0, 0, 0, 0, 0, 0, 0, start|, 0, start|, 0, start|, 0, 0, start|, 0, 0, 0, 0, 0, 0, 0, start|, 0, start|, start|, 0, 0, start|, 0, start|, start|, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0',
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
  '0, start|, 0, final*, start*, 0, 1, final*, 0, final|, start|, 0, 1, final*, start*, 0, final*, 0, 1, final|, start|, 0, final*, start*, 0, final*',
  'ATOM',
  'ATOM',
  'ATOM',
  'ATOM',
  '[',
  '{',
  '1, final*, 0, start|, 0, final*, start*, 0, final*, 0, final|, start|, 0, 1, final*, start*, 0, final*, 0, 1, final|, start|, 0, final*, start*, 0',
  'ATOM',
  '.',
  'ATOM',
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
  '}',
  'ATOM',
  'ATOM',
  'ATOM',
  'ATOM',
  'ATOM',
  'ATOM',
  'ATOM',
  'ATOM',
  'ATOM',
  'ATOM',
  'ATOM',
  'ATOM',
  'ATOM',
  'ATOM',
  'ATOM',
  'ATOM',
  '2',
  '2',
  '2',
  'ATOM',
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
  'ATOM',
  'ATOM',
  'ATOM',
  'STRING',
  'ATOM',
  'ATOM',
  '0, final*, start*, 2, final*, 0, start|, 0, final*, start*, final*, 0, final*, start*, 0, final*, 0, final|, start|, 0, 1, final*, start*, final*, 0, final*, start*, 0, final*, 0, 1, final|, start|, 0, final*, start*, final*, 0, final|, 1, final*, 0, start|, 0, final*, start*, final*, start*, 0, final*, 0, final*, 1, final|, final*, 0, start|, 0, final*, start*, final*, start*, 0, final*, 0, final*, final*, 0, final|, start|, 0, 1, final*, start*, final*, start*, 0, final*, 0, final*, 0, 1, final|, start|, 0, final*, start*, final*, start*, 0, final*, 0',
  'ATOM',
  'ATOM',
  '0, start|, 0, final*, 1, final*, 0, final*, start*, 0, 1, 0, start|, 0, final*, 1, final*, 0, 1, final*, start*, 0, 1',
  'final|, 1, final*, 0, start|, 0, final*, start*, final*, start*, final*, 0, final*, 0, 1, final*, start*, 0, final*, 0, final*',
  'IGNORE',
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
  'FLOAT']), {'IGNORE': None})

# generated code between this line and its other occurence

if __name__ == '__main__':
    f = py.path.local(__file__)
    oldcontent = f.read()
    s = "# GENERATED CODE BETWEEN THIS LINE AND ITS OTHER OCCURENCE\n".lower()
    pre, gen, after = oldcontent.split(s)

    lexer, parser_fact, parser_query, basic_rules = make_all()
    newcontent = ("%s%s\nparser_fact = %r\nparser_query = %r\n%s\n"
                  "\n%s%s") % (
            pre, s, parser_fact, parser_query, lexer.get_dummy_repr(),
            s, after)
    print newcontent
    f.write(newcontent)

import py
from pypy.rlib.parsing.tree import Nonterminal, Symbol, RPythonVisitor
from pypy.rlib.parsing.parsing import PackratParser, Symbol, ParseError, Rule
from pypy.rlib.parsing.ebnfparse import parse_ebnf, make_parse_function
from pypy.rlib.parsing.test.test_parse import EvaluateVisitor


def test_simple():
    regexs, rules, transformer = parse_ebnf("""
IGNORE: " ";
DECIMAL: "0|[1-9][0-9]*";
additive: multitive "+" additive | multitive;
multitive: primary "*" multitive | primary; #nonsense!
# the following too!
primary: "(" additive ")" | DECIMAL;
""")
    class MyEvalVisitor(EvaluateVisitor):
        def visit_primary(self, node):
            if len(node.children) == 3:
                return node.children[1].visit(self)
            return int(node.children[0].additional_info)
    parse = make_parse_function(regexs, rules)
    tree = parse("0 + 10 + 999")
    assert tree.visit(MyEvalVisitor()) == 10 + 999
    tree = parse("22 * 12 + 44)")
    r = tree.visit(MyEvalVisitor())
    assert r == 22 * 12 + 44
    tree = parse("2*(3+5*2*(2+61))")
    assert tree.visit(MyEvalVisitor()) == 2 * (3 + 5 * 2 * (2 + 61))

def test_long_inline_quotes():
    regexs, rules, transformer = parse_ebnf("""
DECIMAL: "0|[1-9][0-9]*";
IGNORE: " ";
additive: multitive "+!" additive | multitive;
multitive: primary "*!" multitive | primary; #nonsense!
primary: "(" additive ")" | DECIMAL;
""")
    class MyEvalVisitor(EvaluateVisitor):
        def visit_primary(self, node):
            if len(node.children) == 3:
                return node.children[1].visit(self)
            return int(node.children[0].additional_info)
    parse = make_parse_function(regexs, rules)
    tree = parse("0 +! 10 +! 999")
    assert tree.visit(MyEvalVisitor()) == 10 + 999

def test_toast():
    regexs, rules, transformer = parse_ebnf("""
DECIMAL: "0|[1-9][0-9]*";
IGNORE: " ";
additive: multitive ["+!"] additive | <multitive>;
multitive: primary ["*!"] multitive | <primary>; #nonsense!
primary: "(" <additive> ")" | <DECIMAL>;
""")
    parse = make_parse_function(regexs, rules)
    print transformer
    ns = {"RPythonVisitor": RPythonVisitor, "Nonterminal": Nonterminal}
    exec py.code.Source(transformer).compile() in ns
    ToAST = ns["ToAST"]
    tree = parse("(0 +! 10) *! (999 +! 10) +! 1")
    print transformer
    tree = tree.visit(ToAST())
    assert len(tree.children) == 2
    assert tree.children[0].children[0].symbol == "additive"
    assert tree.children[1].symbol == "DECIMAL"

def test_eof():
    grammar = """
DECIMAL: "0|[1-9][0-9]*";
IGNORE: " ";
expr: additive0_9 EOF;
additive0_9: multitive "+!" additive0_9 | multitive;
multitive: primary "*!" multitive | primary; #nonsense!
primary: "(" additive0_9 ")" | DECIMAL;
"""
    regexs, rules, transformer = parse_ebnf(grammar)
    class MyEvalVisitor(EvaluateVisitor):
        def visit_primary(self, node):
            if len(node.children) == 3:
                return node.children[1].visit(self)
            return int(node.children[0].additional_info)
        def visit_expr(self, node):
            return node.children[0].visit(self)
        visit_additive0_9 = EvaluateVisitor.visit_additive
    parse = make_parse_function(regexs, rules, eof=True)
    tree = parse("0 +! 10 +! 999")
    assert tree.visit(MyEvalVisitor()) == 10 + 999
    py.test.raises(ParseError, parse, "0 +! 10 +! 999 0000")
    grammar += "some garbage here"
    py.test.raises(ParseError, parse_ebnf, grammar)


def test_prolog():
    regexs, rules, transformer = parse_ebnf("""
ATOM: "[a-z]([a-zA-Z0-9]|_)*";
VAR: "[A-Z]([a-zA-Z0-9]|_)*|_";
NUMBER: "0|[1-9][0-9]*";
IGNORE: "[ \\n\\t]";
file: fact file | fact;
fact: complexterm "." | complexterm ":-" compoundexpr ".";
compoundexpr: complexterm "," compoundexpr | complexterm ";" compoundexpr | complexterm;
complexterm: ATOM "(" exprlist ")" | ATOM;
exprlist: expr "," exprlist | expr;
expr: complexterm | ATOM | NUMBER | VAR;
""")
    parse = make_parse_function(regexs, rules)
    tree = parse("prefix(\n\tlonger(and_nested(term(X))), Xya, _, X0, _).")
    assert tree is not None
    tree = parse("""
foo(X, Y) :- bar(Y, X), bar(Y, X) ; foobar(X, Y, 1234, atom).""")
    assert tree is not None

def test_toast_bigger():
    regexs, rules, transformer = parse_ebnf("""
BOOLCONST: "TRUE|FALSE";
IDENTIFIER: "[a-zA-Z_][a-zA-Z0-9_]*";
NUMBER: "0|[1-9][0-9]*";
IGNORE: " ";
# expression
expr: <intexpr> | <boolexpr>;
intexpr: multitive "+" intexpr | multitive "-" intexpr | <multitive>;
multitive: primary "*" unaryexpr | primary "/" unaryexpr |
           primary "%" unaryexpr | <unaryexpr>;
unaryexpr: "+" unaryexpr | "-" unaryexpr | <primary>;
primary: "(" <intexpr> ")" | <NUMBER> | <IDENTIFIER>;
boolexpr: <BOOLCONST>; #XXX
""")
    parse = make_parse_function(regexs, rules)
    tree = parse("x * floor + 1")
    print transformer
    ns = {"RPythonVisitor": RPythonVisitor, "Nonterminal": Nonterminal}
    exec py.code.Source(transformer).compile() in ns
    ToAST = ns["ToAST"]
    tree = tree.visit(ToAST())
    assert tree.children[2].symbol == "NUMBER"

def test_parser_repr_is_evalable():
    regexs, rules, transformer = parse_ebnf("""
BOOLCONST: "TRUE|FALSE";
IDENTIFIER: "[a-zA-Z_][a-zA-Z0-9_]*";
NUMBER: "0|[1-9][0-9]*";
IGNORE: " ";
# expression
expr: <intexpr> | <boolexpr>;
intexpr: multitive "+" intexpr | multitive "-" intexpr | <multitive>;
multitive: primary "*" unaryexpr | primary "/" unaryexpr |
           primary "%" unaryexpr | <unaryexpr>;
unaryexpr: "+" unaryexpr | "-" unaryexpr | <primary>;
primary: "(" <intexpr> ")" | <NUMBER> | <IDENTIFIER>;
boolexpr: <BOOLCONST>; #XXX

""")
    parser = PackratParser(rules, rules[0].nonterminal)
    s = repr(parser)
    print s
    newparser = eval(s)
    assert repr(newparser) == s

def test_lexer_end_string_corner_case():
    regexs, rules, transformer = parse_ebnf("""
NUMBER: "[0-9]*(\.[0-9]+)?";
ATOM: "\.";
IGNORE: " ";
expr: NUMBER ATOM EOF;
""")
    parse = make_parse_function(regexs, rules, eof=True)
    t = parse("2.")
    assert t.children[0].additional_info == "2"
    assert t.children[1].additional_info == "."

def test_escape_quotes():
    regexs, rules, transformer = parse_ebnf("""
QUOTE: "a\\"";
IGNORE: " ";
expr: QUOTE "\\"" EOF;""")
    parse = make_parse_function(regexs, rules, eof=True)
    t = parse('a" "')
    assert t.children[0].additional_info == 'a"'
    assert t.children[1].additional_info == '"'

def test_leftrecursion():
    regexs, rules, transformer = parse_ebnf("""
A: "a";
B: "b";
IGNORE: " |\n";
expr1: A | expr2 A;
expr2: expr1 B;
""")
    py.test.raises(AssertionError, make_parse_function, regexs, rules, True)

def test_dictparse():
    regexs, rules, transformer = parse_ebnf("""
    QUOTED_STRING: "'[^\\']*'";
    IGNORE: " |\n";
    data: <dict> | <QUOTED_STRING> | <list>;
    dict: ["{"] (dictentry [","])* dictentry ["}"];
    dictentry: QUOTED_STRING [":"] data;
    list: ["["] (data [","])* data ["]"];
""")
    parse = make_parse_function(regexs, rules, eof=True)
    t = parse("""
{
    'type': 'SCRIPT',
    '0': {
        'type': 'SEMICOLON',
        'end': '5',
        'expression': {
            'type': 'ASSIGN',
            '0': {
                'type': 'IDENTIFIER',
                'assignOp': 'null',
                'end': '1',
                'lineno': '1',
                'start': '0',
                'tokenizer': '[object Object]',
                'value': 'x'
            } ,
            '1': {
                'type': 'NUMBER',
                'end': '5',
                'lineno': '1',
                'start': '4',
                'tokenizer': '[object Object]',
                'value': '1'
            } ,
            'end': '5',
            'length': '2',
            'lineno': '1',
            'start': '0',
            'tokenizer': '[object Object]',
            'value': '='
        } ,
        'lineno': '1',
        'start': '0',
        'tokenizer': '[object Object]',
        'value': 'x'
    } ,
    'funDecls': '',
    'length': '1',
    'lineno': '1',
    'tokenizer': '[object Object]',
    'varDecls': ''
}""")
    ns = {"RPythonVisitor": RPythonVisitor, "Nonterminal": Nonterminal}
    exec py.code.Source(transformer).compile() in ns
    ToAST = ns["ToAST"]
    print transformer
    t = t.visit(ToAST())

def test_starparse():
    regexs, rules, transformer = parse_ebnf("""
    QUOTED_STRING: "'[^\\']*'";
    IGNORE: " |\n";
    list: ["["] (QUOTED_STRING [","])* QUOTED_STRING ["]"];
""")
    parse = make_parse_function(regexs, rules, eof=True)
    t = parse("""['a', 'b', 'c']""")
    print transformer
    exec py.code.Source(transformer).compile()
    t = t.visit(ToAST())
    assert t.symbol == "list"
    assert len(t.children) == 2
    assert t.children[0].symbol == "__list"
    assert len(t.children[0].children) == 2
    assert [c.symbol for c in t.children[0].children] == ["QUOTED_STRING"] * 2
    t = parse("['a']")

def test_transform_star():
    py.test.skip("This needs to be fixed - generated transformer is buggy")
    regexs, rules, transformer = parse_ebnf("""
    IGNORE: " ";
    ATOM: "[\+a-zA-Z_][a-zA-Z0-9_]*";

    sexpr: ATOM | list;
    list: "(" sexpr* ")";
""")
    parse = make_parse_function(regexs, rules)
    tree = parse("()")
    print transformer
    ns = {"RPythonVisitor": RPythonVisitor, "Nonterminal": Nonterminal}
    exec py.code.Source(transformer).compile() in ns
    ToAST = ns["ToAST"]
    list_expr = tree.visit(ToAST()).children[0]
    assert list_expr.symbol == 'list'
    # should have two children, "(" and ")"
    assert len(list_expr.children) == 2
    assert list_expr.children[0].symbol == '('
    assert list_expr.children[1].symbol == ')'


def test_quoting():
    regexs, rules, transformer = parse_ebnf("""
    ATOM: "[a-z]*";
    IGNORE: " ";
    list: ATOM "\n" ATOM;
""")
    parse = make_parse_function(regexs, rules, eof=True)
    t = parse("""abc
  abd""")
    assert len(t.children) == 3
    assert t.children[1].additional_info == "\n"

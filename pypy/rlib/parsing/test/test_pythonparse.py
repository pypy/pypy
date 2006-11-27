""" test file to experiment with a an adapted CPython grammar """

import py
from pypy.rlib.parsing.lexer import Lexer
from pypy.rlib.parsing.deterministic import LexerError
from pypy.rlib.parsing.tree import Nonterminal, Symbol, RPythonVisitor
from pypy.rlib.parsing.parsing import PackratParser, Symbol, ParseError, Rule
from pypy.rlib.parsing.ebnfparse import parse_ebnf, make_parse_function

grammar = py.magic.autopath().dirpath().join("pygrammar.txt").read()


def test_parse_grammar():
    _, rules, ToAST = parse_ebnf(grammar)

def test_parse_python_args():
    regexs, rules, ToAST = parse_ebnf("""
IGNORE: " ";
NAME: "[a-zA-Z_]*";
NUMBER: "0|[1-9][0-9]*";
parameters: ["("] >varargslist< [")"] | ["("] [")"];
varargslist: (fpdef ("=" test)? ",")* star_or_starstarargs |
             fpdef ("=" test)? ("," fpdef ("=" test)?)* ","?;
star_or_starstarargs:  "*" NAME "," "**" NAME | "*" NAME | "**" NAME;
fpdef: NAME | "(" fplist ")";
fplist: fpdef ("," fpdef)* ","?;
test: NUMBER;
    """)
    parse = make_parse_function(regexs, rules)
    t = parse("(a)").visit(ToAST())[0]
    t = parse("(a,)").visit(ToAST())[0]
    t = parse("(a,b,c,d)").visit(ToAST())[0]
    t = parse("(a,b,c,d,)").visit(ToAST())[0]
    t = parse("((a, b, c),b,c,d,)").visit(ToAST())[0]
    t = parse("((a, b, c),b,c,d,*args)").visit(ToAST())[0]
    t = parse("((a, b, c),b,c,d,**kwargs)").visit(ToAST())[0]
    t = parse("((a, b, c),b,c,d,*args, **args)").visit(ToAST())[0]
    t = parse("()").visit(ToAST())[0]
    t = parse("(*args, **args)").visit(ToAST())[0]
    t = parse("(a=1)").visit(ToAST())[0]
    t = parse("(a=2,)").visit(ToAST())[0]
    t = parse("(a,b,c,d=3)").visit(ToAST())[0]
    t = parse("(a,b,c,d=4,)").visit(ToAST())[0]
    t = parse("((a, b, c),b,c,(c, d)=1,)").visit(ToAST())[0]
    t = parse("((a, b, c),b,c,d=1,*args)").visit(ToAST())[0]
    t = parse("((a, b, c),b,c,d=2,**kwargs)").visit(ToAST())[0]
    t = parse("((a, b, c),b,c,(c, d)=4,*args, **args)").visit(ToAST())[0]
    t = parse("(self, a, b, args)").visit(ToAST())[0]
    
def test_parse_funcdef():
    regexs, rules, ToAST = parse_ebnf("""
IGNORE: " ";
NAME: "[a-zA-Z_]*";
NUMBER: "0|[1-9][0-9]*";
funcdef: "def" NAME parameters ":" suite;
parameters: ["("] >varargslist< [")"] | ["("] [")"];
varargslist: (fpdef ("=" test)? ",")* star_or_starstarargs |
             fpdef ("=" test)? ("," fpdef ("=" test)?)* ","?;
star_or_starstarargs:  "*" NAME "," "**" NAME | "*" NAME | "**" NAME;
fpdef: NAME | "(" fplist ")";
fplist: fpdef ("," fpdef)* ","?;
test: NUMBER;
suite: simple_stmt | ["NEWLINE"] ["INDENT"] stmt+ ["DEDENT"];
simple_stmt: stmt;
stmt: "pass";
    """)
    parse = make_parse_function(regexs, rules)
    t = parse("def f(a): NEWLINE INDENT pass DEDENT").visit(ToAST())[0]


class TestParser(object):
    def setup_class(cls):
        from pypy.rlib.parsing.parsing import PackratParser
        regexs, rules, ToAST = parse_ebnf(grammar)
        cls.ToAST = ToAST()
        cls.parser = PackratParser(rules, rules[0].nonterminal)
        cls.regexs = regexs
        names, regexs = zip(*regexs)
        cls.lexer = Lexer(list(regexs), list(names))

    def parse(self, source):
        tokens = list(self.tokenize(source))
        s = self.parser.parse(tokens)
        return s

    def tokenize(self, source):
        # use tokenize module but rewrite tokens slightly
        import tokenize, cStringIO
        pos = 0
        readline = cStringIO.StringIO(source).readline
        for token in tokenize.generate_tokens(readline):
            typ, s, (row, col), _, line = token
            pos += len(s)
            typ = tokenize.tok_name[typ]
            if typ == "ENDMARKER":
                typ = s = "EOF"
            elif typ == "NL":
                continue
            elif typ == "COMMENT":
                continue
            try:
                tokens = self.lexer.tokenize(s, eof=False)
                if len(tokens) == 1:
                    typ, s, _, _, _ = tokens[0]
                    yield typ, s, pos, row, col
                    continue
            except LexerError:
                pass
            yield (typ, s, pos, row, col)


    def test_simple(self):
        t = self.parse("""
def f(x, null=0):
    if x >= null:
        return null + x
    else:
        pass
        return null - x
        """)
        t = t.visit(self.ToAST)
        assert len(t) == 1
        t = t[0]

    def test_class(self):
        t = self.parse("""
class A(object):
    def __init__(self, a, b, *args):
        self.a = a
        self.b = b
        if args:
            self.len = len(args)
            self.args = [a, b] + list(args)

    def diagonal(self):
        return (self.a ** 2 + self.b ** 2) ** 0.5
        """)
        t = t.visit(self.ToAST)[0]

    def test_while(self):
        t = self.parse("""
def f(x, null=0):
    i = null
    result = 0
    while i < x:
        result += i
        i += 1
        if result % 625 == 13:
            break
    else:
        return result - 15
    return result
        """)
        t = t.visit(self.ToAST)
        assert len(t) == 1
        t = t[0]

    def test_comment(self):
        t = self.parse("""
def f(x):
    # this does some fancy stuff
    return x
""")
        t = self.ToAST.transform(t)

    def test_parse_this(self):
        s = py.magic.autopath().read()
        s = s[s.index("\nclass"):]
        t = self.parse(s)
        t = t.visit(self.ToAST)[0]

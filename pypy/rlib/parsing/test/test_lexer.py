import py
from pypy.rlib.parsing.lexer import *
from pypy.rlib.parsing.regex import *
from pypy.rlib.parsing import deterministic


class TestDirectLexer(object):
    def get_lexer(self, rexs, names, ignore=None):
        return Lexer(rexs, names, ignore)

    def test_simple(self):
        rexs = [StringExpression("if"), StringExpression("else"),
                StringExpression("while"), StringExpression(":"),
                StringExpression(" ")]
        names = ["IF", "ELSE", "WHILE", "COLON", "WHITE"]
        l = self.get_lexer(rexs, names)
        r = l.get_runner("if: else: while:")
        t = r.find_next_token()
        assert t == ("IF", "if", 0, 0, 0)
        t = r.find_next_token()
        assert t == ("COLON", ":", 2, 0, 2)
        t = r.find_next_token()
        assert t == ("WHITE", " ", 3, 0, 3)
        t = r.find_next_token()
        assert t == ("ELSE", "else", 4, 0, 4)
        t = r.find_next_token()
        assert t == ("COLON", ":", 8, 0, 8)
        t = r.find_next_token()
        assert t == ("WHITE", " ", 9, 0, 9)
        t = r.find_next_token()
        assert t == ("WHILE", "while", 10, 0, 10)
        t = r.find_next_token()
        assert t == ("COLON", ":", 15, 0, 15)
        py.test.raises(StopIteration, r.find_next_token)
        assert [t[0] for t in l.tokenize("if if if: else while")] == "IF WHITE IF WHITE IF COLON WHITE ELSE WHITE WHILE".split()

    def test_pro(self):
        digits = RangeExpression("0", "9")
        lower = RangeExpression("a", "z")
        upper = RangeExpression("A", "Z")
        keywords = StringExpression("if") | StringExpression("else") | StringExpression("def") | StringExpression("class")
        underscore = StringExpression("_")
        atoms = lower + (upper | lower | digits | underscore).kleene()
        vars = underscore | (upper + (upper | lower | underscore | digits).kleene())
        integers = StringExpression("0") | (RangeExpression("1", "9") + digits.kleene())
        white = StringExpression(" ")
        l = self.get_lexer([keywords, atoms, vars, integers, white], ["KEYWORD", "ATOM", "VAR", "INT", "WHITE"])
        assert ([t[0] for t in l.tokenize("if A a 12341 0 else")] ==
                "KEYWORD WHITE VAR WHITE ATOM WHITE INT WHITE INT WHITE KEYWORD".split())

    def test_ignore(self):
        rexs = [StringExpression("if"), StringExpression("else"),
                StringExpression("while"), StringExpression(":"),
                StringExpression(" ")]
        names = ["IF", "ELSE", "WHILE", "COLON", "WHITE"]
        l = self.get_lexer(rexs, names, ["WHITE"])
        assert [t[0] for t in l.tokenize("if if if: else while")] == "IF IF IF COLON ELSE WHILE".split()
      
    def test_errors(self):
        rexs = [StringExpression("if"), StringExpression("else"),
                StringExpression("while"), StringExpression(":"),
                StringExpression(" ")]
        names = ["IF", "ELSE", "WHILE", "COLON", "WHITE"]
        l = self.get_lexer(rexs, names, ["WHITE"])
        info = py.test.raises(deterministic.LexerError, l.tokenize, "if if if: a else while")
        print dir(info)
        print info.__class__
        exc = info.value
        assert exc.input[exc.index] == "a"

    def test_eof(self):
        rexs = [StringExpression("if"), StringExpression("else"),
                StringExpression("while"), StringExpression(":"),
                StringExpression(" ")]
        names = ["IF", "ELSE", "WHILE", "COLON", "WHITE"]
        l = self.get_lexer(rexs, names, ["WHITE"])
        s = "if if if: else while"
        tokens = list(l.get_runner(s, eof=True))
        print tokens
        assert tokens[-1] == ("EOF", "EOF", len(s), 0, len(s))
        tokens = l.tokenize(s, eof=True)
        print tokens
        assert tokens[-1] == ("EOF", "EOF", len(s), 0, len(s))

    def test_position(self):
        rexs = [StringExpression("if"), StringExpression("else"),
                StringExpression("while"), StringExpression(":"),
                StringExpression(" "), StringExpression("\n")]
        names = ["IF", "ELSE", "WHILE", "COLON", "WHITE", "NL"]
        l = self.get_lexer(rexs, names, ["WHITE"])
        s = "if\nif if:\nelse while\n"
        tokens = list(l.get_runner(s, eof=True))
        assert tokens[0] == ("IF", "if", 0, 0, 0)
        assert tokens[1] == ("NL", "\n", 2, 0, 2)
        assert tokens[2] == ("IF", "if", 3, 1, 0)
        assert tokens[3] == ("IF", "if", 6, 1, 3)
        assert tokens[4] == ("COLON", ":", 8, 1, 5)
        assert tokens[5] == ("NL", "\n", 9, 1, 6)
        assert tokens[6] == ("ELSE", "else", 10, 2, 0)
        assert tokens[7] == ("WHILE", "while", 15, 2, 5)
        assert tokens[8] == ("NL", "\n", 20, 2, 10)
        assert tokens[9] == ("EOF", "EOF", 21, 3, 0)

    def test_position_ignore(self):
        rexs = [StringExpression("if"), StringExpression("else"),
                StringExpression("while"), StringExpression(":"),
                StringExpression(" "), StringExpression("\n")]
        names = ["IF", "ELSE", "WHILE", "COLON", "WHITE", "NL"]
        l = self.get_lexer(rexs, names, ["WHITE", "NL"])
        s = "if\nif if:\nelse while\n"
        tokens = list(l.get_runner(s, eof=True))
        assert tokens[0] == ("IF", "if", 0, 0, 0)
        assert tokens[1] == ("IF", "if", 3, 1, 0)
        assert tokens[2] == ("IF", "if", 6, 1, 3)
        assert tokens[3] == ("COLON", ":", 8, 1, 5)
        assert tokens[4] == ("ELSE", "else", 10, 2, 0)
        assert tokens[5] == ("WHILE", "while", 15, 2, 5)
        assert tokens[6] == ("EOF", "EOF", 21, 3, 0)


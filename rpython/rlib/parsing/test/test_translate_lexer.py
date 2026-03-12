from rpython.rlib.parsing.lexer import *
from rpython.rlib.parsing.regex import *
from rpython.translator.c.test.test_genc import compile

def test_translate_simple():
    digits = RangeExpression("0", "9")
    lower = RangeExpression("a", "z")
    upper = RangeExpression("A", "Z")
    keywords = StringExpression("if") | StringExpression("else") | StringExpression("def") | StringExpression("class")
    underscore = StringExpression("_")
    atoms = lower + (upper | lower | digits | underscore).kleene()
    vars = underscore | (upper + (upper | lower | underscore | digits).kleene())
    integers = StringExpression("0") | (RangeExpression("1", "9") + digits.kleene())
    white = StringExpression(" ")
    token_regexes = [keywords, atoms, vars, integers, white]
    names = ["KEYWORD", "ATOM", "VAR", "INT", "WHITE"]
    l1 = Lexer(token_regexes, names, None)
    l2 = Lexer(token_regexes, names, ["WHITE"])

    def lex(s, ignore=False):
        if ignore:
            tokens = l2.tokenize(s)
        else:
            tokens = l1.tokenize(s)
        return "-%-".join([t.name for t in tokens])

    res = lex("if A a 12341 0 else").split("-%-")
    assert res == ("KEYWORD WHITE VAR WHITE ATOM WHITE INT WHITE "
                   "INT WHITE KEYWORD").split()
    res = lex("if A a 12341 0 else", True).split("-%-")
    assert res == "KEYWORD VAR ATOM INT INT KEYWORD".split()

    func = compile(lex, [str, bool])
    res = func("if A a 12341 0 else", False).split("-%-")
    assert res == ("KEYWORD WHITE VAR WHITE ATOM WHITE INT WHITE "
                   "INT WHITE KEYWORD").split()
    res = func("if A a 12341 0 else", True).split("-%-")
    assert res == "KEYWORD VAR ATOM INT INT KEYWORD".split()


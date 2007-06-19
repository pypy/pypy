import py
from pypy.rlib.parsing.regexparse import make_runner, unescape
from pypy.rlib.parsing import regex
import operator
from pypy.rlib.parsing.makepackrat import PackratParser as _PackratParser
from pypy.rlib.parsing.deterministic import compress_char_set, DFA

class RegexParser(_PackratParser):
    r"""
    EOF:
        !__any__;

    parse:
        regex
        [EOF];

    regex:
        r1 = concatenation
        '|'
        r2 = regex
        return {r1 | r2}
      | concatenation;

    concatenation:
        l = repetition+
        return {reduce(operator.add, l, regex.StringExpression(""))};

    repetition:
        r1 = primary
        '*'
        return {r1.kleene()}
      | r1 = primary
        '+'
        return {r1 + r1.kleene()}
      | r1 = primary
        '?'
        return {regex.StringExpression("") | r1}
      | r = primary
        '{'
        n = numrange
        '}'
        return {r * n[0] + reduce(operator.or_, [r * i for i in range(n[1] - n[0] + 1)], regex.StringExpression(""))}
      | primary;

    primary:
        ['('] regex [')']
      | range
      | c = char
        return {regex.StringExpression(c)}
      | '.'
        return {regex.RangeExpression(chr(0), chr(255))};

    char:
        c = QUOTEDCHAR
        return {unescape(c)}
      | c = CHAR
        return {c};

    QUOTEDCHAR:
        `(\\x[0-9a-fA-F]{2})|(\\.)`;

    CHAR:
        `[^\*\+\(\)\[\]\{\}\|\.\-\?\,\^]`;

    range:
        '['
        s = rangeinner
        ']'
        return {reduce(operator.or_, [regex.RangeExpression(a, chr(ord(a) + b - 1)) for a, b in compress_char_set(s)])};

    rangeinner:
        '^'
        s = subrange
        return {set([chr(c) for c in range(256)]) - s}
      | subrange;

    subrange:
        l = rangeelement+
        return {reduce(operator.or_, l)};

    rangeelement:
        c1 = char
        '-'
        c2 = char
        return {set([chr(i) for i in range(ord(c1), ord(c2) + 1)])}
      | c = char
        return {set([c])};

    numrange:
        n1 = NUM
        ','
        n2 = NUM
        return {n1, n2}
      | n1 = NUM
        return {n1, n1};

    NUM:
        c = `0|([1-9][0-9]*)`
        return {int(c)};
    """



def make_runner(regex, view=False):
    p = RegexParser(regex)
    r = p.parse()
    nfa = r.make_automaton()
    dfa = nfa.make_deterministic()
    if view:
        dfa.view()
    dfa.optimize()
    if view:
        dfa.view()
    r = dfa.get_runner()
    return r


def test_simple():
    r = make_runner("a*")
    assert r.recognize("aaaaa")
    assert r.recognize("")
    assert not r.recognize("aaaaaaaaaaaaaaaaaaaaaaaaaa ")
    r = make_runner("a*bc|d")
    assert r.recognize("aaaaabc")
    assert r.recognize("bc")
    assert r.recognize("d")
    assert not r.recognize("abcd")
    r = make_runner("(ab)*|a*b*")
    assert r.recognize("ababababab")
    assert r.recognize("aaaabb")
    assert not r.recognize("abababaabb")
    r = make_runner(".*")
    assert r.recognize("kjsadfq3jlflASDF@#$")
    assert r.recognize("vka afj ASF# A")

def test_quoted():
    r = make_runner("\\(*")
    assert r.recognize("(")
    assert not r.recognize("\\(")
    r = make_runner("(\\x61a)*")
    assert r.recognize("aa")
    assert r.recognize("aaaaaa")
    assert not r.recognize("a")
    assert not r.recognize("aabb")

def test_range():
    r = make_runner("[A-Z]")
    assert r.recognize("A")
    assert r.recognize("F")
    assert r.recognize("Z")
    assert not r.recognize("j")
    r = make_runner("[a-ceg-i]")
    assert r.recognize("a")
    assert r.recognize("b")
    assert r.recognize("c")
    assert r.recognize("e")
    assert r.recognize("g")
    assert r.recognize("h")
    assert r.recognize("i")
    assert not r.recognize("d")
    assert not r.recognize("f")
    r = make_runner("[^a-ceg-i]")
    assert not r.recognize("a")
    assert not r.recognize("b")
    assert not r.recognize("c")
    assert not r.recognize("e")
    assert not r.recognize("g")
    assert not r.recognize("h")
    assert not r.recognize("i")
    assert r.recognize("d")
    assert r.recognize("f")

def test_plus():
    r = make_runner("[0-9]+")
    assert r.recognize("09123")
    assert not r.recognize("")
    r = make_runner("a+b+")
    assert r.recognize("ab")
    assert r.recognize("aaaaabbb")
    assert not r.recognize("b")
    assert not r.recognize("a")
    assert not r.recognize("c")

def test_quoted():
    r = make_runner('\\[|\\]|\\|')
    assert r.recognize("[")
    assert r.recognize("|")
    assert r.recognize("]")
    assert not r.recognize("]]")

def test_questionmark():
    r = make_runner("ab?")
    assert r.recognize("a")
    assert r.recognize("ab")
    r = make_runner("0|(\\+|\\-)?[1-9][0-9]*")
    assert r.recognize("0")
    assert not r.recognize("00")
    assert r.recognize("12341")
    assert not r.recognize("021314")
    assert r.recognize("+12314")
    assert r.recognize("-12314")

def test_repetition():
    r = make_runner('a{15}')
    assert r.recognize("a" * 15)
    assert not r.recognize("a" * 14)
    assert not r.recognize("a" * 16)
    assert not r.recognize("b" * 16)
    r = make_runner('a{2,10}')
    assert r.recognize("a" * 2)
    assert r.recognize("a" * 5)
    assert r.recognize("a" * 10)
    assert not r.recognize("a")
    assert not r.recognize("a" + "b")
    assert not r.recognize("a" * 11)
    assert not r.recognize("a" * 12)

def test_quotes():
    r = make_runner('"[^\\"]*"')
    assert r.recognize('"abc"')
    assert r.recognize('"asdfefveeaa"')
    assert not r.recognize('"""')
    r = make_runner('\\n\\x0a')
    assert not r.recognize("n\n")
    assert r.recognize("\n\n")

def test_comment():
    r = make_runner("(/\\*[^\\*/]*\\*/)")
    assert r.recognize("/*asdfasdfasdf*/")

def test_singlequote():
    r = make_runner("'")
    assert r.recognize("'")
    assert not r.recognize('"')
    r = make_runner("'..*'")
    assert r.recognize("'adadf'")
    assert not r.recognize("'adfasdf")
    r = make_runner("([a-z]([a-zA-Z0-9]|_)*)|('..*')")
    assert r.recognize("aasdf")
    assert r.recognize("'X'")
    assert not r.recognize("''")

def test_unescape():
    from pypy.rlib.parsing.regexparse import unescape
    s = "".join(["\\x%s%s" % (a, b) for a in "0123456789abcdefABCDEF"
                    for b in "0123456789ABCDEFabcdef"])
    assert unescape(s) == eval("'" + s + "'")

def test_escaped_quote():
    r = make_runner(r'"[^\\"]*(\\.[^\\"]*)*"')
    assert r.recognize(r'""')
    assert r.recognize(r'"a"')
    assert r.recognize(r'"a\"b"')
    assert r.recognize(r'"\\\""')
    assert not r.recognize(r'"\\""')

def test_number():
    r = make_runner(r"\-?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][\+\-]?[0-9]+)?")
    assert r.recognize("-0.912E+0001")
    assert not r.recognize("-0.a912E+0001")
    assert r.recognize("5")

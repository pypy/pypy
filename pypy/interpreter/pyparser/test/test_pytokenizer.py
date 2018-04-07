import pytest
from pypy.interpreter.pyparser import pytokenizer
from pypy.interpreter.pyparser.pygram import tokens
from pypy.interpreter.pyparser.error import TokenError

def tokenize(s):
    return pytokenizer.generate_tokens(s.splitlines(True) + ["\n"], 0)

def check_token_error(s, msg):
    error = pytest.raises(TokenError, tokenize, s)
    assert error.value.msg == msg


class TestTokenizer(object):

    def test_simple(self):
        line = "a+1"
        tks = tokenize(line)
        assert tks == [
            (tokens.NAME, 'a', 1, 0, line),
            (tokens.PLUS, '+', 1, 1, line),
            (tokens.NUMBER, '1', 1, 2, line),
            (tokens.NEWLINE, '', 2, 0, '\n'),
            (tokens.NEWLINE, '', 2, 0, '\n'),
            (tokens.ENDMARKER, '', 2, 0, ''),
            ]

    def test_error_parenthesis(self):
        for paren in "([{":
            check_token_error(paren + "1 + 2",
                              "parenthesis is never closed")

        for paren in ")]}":
            check_token_error("1 + 2" + paren,
                              "unmatched '%s'" % (paren, ))



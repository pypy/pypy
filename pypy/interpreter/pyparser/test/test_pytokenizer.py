import pytest
from pypy.interpreter.pyparser import pytokenizer
from pypy.interpreter.pyparser.pygram import tokens
from pypy.interpreter.pyparser.error import TokenError

def tokenize(s):
    return pytokenizer.generate_tokens(s.splitlines(True) + ["\n"], 0)

def check_token_error(s, msg, pos=-1):
    error = pytest.raises(TokenError, tokenize, s)
    assert error.value.msg == msg
    if pos != -1:
        assert error.value.offset == pos


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
                              "parenthesis is never closed",
                              0)

        for paren in ")]}":
            check_token_error("1 + 2" + paren,
                              "unmatched '%s'" % (paren, ),
                              5)

        for i, opening in enumerate("([{"):
            for j, closing in enumerate(")]}"):
                if i == j:
                    continue
                error = pytest.raises(TokenError, tokenize, opening + "1\n" + closing)
                assert error.value.msg == \
                        "parenthesis '%s' and '%s' don't match" % (opening, closing)
                assert error.value.offset == 0
                assert error.value.lineno == 1
                assert error.value.lastlineno == 2


    def test_unknown_char(self):
        check_token_error("?", "Unknown character", 0)

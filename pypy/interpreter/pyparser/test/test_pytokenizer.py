import pytest
from pypy.interpreter.pyparser import pytokenizer
from pypy.interpreter.pyparser.pygram import tokens
from pypy.interpreter.pyparser.error import TokenError

def tokenize(s):
    return pytokenizer.generate_tokens(s.splitlines(True) + ["\n"], 0)

def check_token_error(s, msg=None, pos=-1, line=-1):
    error = pytest.raises(TokenError, tokenize, s)
    if msg is not None:
        assert error.value.msg == msg
    if pos != -1:
        assert error.value.offset == pos
    if line != -1:
        assert error.value.lineno == line


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
                              1)

        for paren in ")]}":
            check_token_error("1 + 2" + paren,
                              "unmatched '%s'" % (paren, ),
                              6)

        for i, opening in enumerate("([{"):
            for j, closing in enumerate(")]}"):
                if i == j:
                    continue
                check_token_error(opening + "1\n" + closing,
                        "closing parenthesis '%s' does not match opening parenthesis '%s' on line 1" % (closing, opening),
                        pos=1, line=2)
                check_token_error(opening + "1" + closing,
                        "closing parenthesis '%s' does not match opening parenthesis '%s'" % (closing, opening),
                        pos=3, line=1)
                check_token_error(opening + closing,
                        "closing parenthesis '%s' does not match opening parenthesis '%s'" % (closing, opening),
                        pos=2, line=1)


    def test_unknown_char(self):
        check_token_error("?", "Unknown character", 1)

    def test_eol_string(self):
        check_token_error("x = 'a", pos=5, line=1)

    def test_eof_triple_quoted(self):
        check_token_error("'''", pos=1, line=1)

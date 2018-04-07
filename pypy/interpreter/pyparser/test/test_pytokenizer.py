from pypy.interpreter.pyparser import pytokenizer
from pypy.interpreter.pyparser.pygram import tokens

def tokenize(s):
    return pytokenizer.generate_tokens(s.splitlines(True) + ["\n"], 0)

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

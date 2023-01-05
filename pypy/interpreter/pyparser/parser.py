"""
A CPython inspired RPython parser.
"""
from rpython.rlib.objectmodel import not_rpython

class DFA(object):
    def __init__(self, grammar, symbol_id, states, first):
        self.grammar = grammar
        self.symbol_id = symbol_id
        self.states = states
        self.first = self._first_to_string(first)
        self.grammar = grammar

    def could_match_token(self, label_index):
        pos = label_index >> 3
        bit = 1 << (label_index & 0b111)
        return bool(ord(self.first[label_index >> 3]) & bit)

    @staticmethod
    @not_rpython
    def _first_to_string(first):
        l = sorted(first.keys())
        b = bytearray(32)
        for label_index in l:
            pos = label_index >> 3
            bit = 1 << (label_index & 0b111)
            b[pos] |= bit
        return str(b)

class TokenASTBase(object):
    _attrs_ = []

class Token(TokenASTBase):
    def __init__(self, token_type, value, lineno, column, line, end_lineno=-1, end_column=-1):
        self.token_type = token_type
        self.value = value
        self.lineno = lineno
        # 0-based offset
        self.column = column
        self.line = line
        self.end_lineno = end_lineno
        self.end_column = end_column

    def __repr__(self):
        from pypy.interpreter.pyparser.pytoken import token_names
        return "Token(%s, %s)" % (token_names.get(self.token_type, self.token_type), self.value)

    def __eq__(self, other):
        # for tests
        return (
            self.token_type == other.token_type and
            self.value == other.value and
            self.lineno == other.lineno and
            self.column == other.column and
            self.line == other.line and
            self.end_lineno == other.end_lineno and
            self.end_column == other.end_column
        )

    def __ne__(self, other):
        return not self == other

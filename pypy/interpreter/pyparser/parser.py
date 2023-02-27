"""
A CPython inspired RPython parser.
"""

class TokenASTBase(object):
    _attrs_ = []

class Token(TokenASTBase):
    def __init__(self, token_type, value, lineno, column, line, end_lineno=-1, end_column=-1, level=0):
        self.token_type = token_type
        self.value = value
        self.lineno = lineno
        # 0-based offset
        self.column = column
        self.line = line
        self.end_lineno = end_lineno
        self.end_column = end_column
        self.level = level

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

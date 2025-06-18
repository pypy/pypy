# -*- coding: utf-8 -* -
import pytest
from pypy.interpreter.astcompiler import consts
from pypy.interpreter.pyparser import pytokenizer
from pypy.interpreter.pyparser.parser import Token
from pypy.interpreter.pyparser.pygram import tokens
from pypy.interpreter.pyparser.error import TokenError

def tokenize(s, flags=0):
    source_lines = s.splitlines(True)
    if source_lines and not source_lines[-1].endswith("\n"):
        source_lines[-1] += '\n'
    return pytokenizer.generate_tokens(source_lines, flags)

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
        line = "a+1\n"
        tks = tokenize(line)
        assert tks[:-3] == [
            Token(tokens.NAME, 'a', 1, 0, line, 1, 1),
            Token(tokens.PLUS, '+', 1, 1, line, 1, 2),
            Token(tokens.NUMBER, '1', 1, 2, line, 1, 3),
            ]

    def test_error_parenthesis(self):
        for paren in "([{":
            check_token_error(paren + "1 + 2",
                              "'%s' was never closed" % paren,
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
        check_token_error("?", "invalid character '?' (U+003F)", 1)
        check_token_error("$", "invalid character '$' (U+0024)", 1)
        check_token_error("⫛", "invalid character '⫛' (U+2ADB)", 1)
        check_token_error("\x17", "invalid non-printable character U+0017", 1)

    def test_eol_string(self):
        check_token_error("x = 'a", pos=5, line=1)

    def test_eof_triple_quoted(self):
        check_token_error("'''", pos=1, line=1)

    def test_type_comments(self):
        line = "a = 5 # type: int\n"
        tks = tokenize(line, flags=consts.PyCF_TYPE_COMMENTS)
        assert tks[:-3] == [
            Token(tokens.NAME, 'a', 1, 0, line, 1, 1),
            Token(tokens.EQUAL, '=', 1, 2, line, 1, 3),
            Token(tokens.NUMBER, '5', 1, 4, line, 1, 5),
            Token(tokens.TYPE_COMMENT, 'int', 1, 6, line),
        ]

    def test_type_comment_bug(self):
        lines = ['# type: int\n', '']
        pytokenizer.generate_tokens(lines, flags=consts.PyCF_TYPE_COMMENTS)

    def test_type_ignore(self):
        line = "a = 5 # type: ignore@teyit\n"
        tks = tokenize(line, flags=consts.PyCF_TYPE_COMMENTS)
        assert tks[:-3] == [
            Token(tokens.NAME, 'a', 1, 0, line, 1, 1),
            Token(tokens.EQUAL, '=', 1, 2, line, 1, 3),
            Token(tokens.NUMBER, '5', 1, 4, line, 1, 5),
            Token(tokens.TYPE_IGNORE, '@teyit', 1, 6, line),
        ]

    def test_walrus(self):
        line = "a:=1\n"
        tks = tokenize(line)
        assert tks[:-3] == [
            Token(tokens.NAME, 'a', 1, 0, line, 1, 1),
            Token(tokens.COLONEQUAL, ':=', 1, 1, line, 1, 3),
            Token(tokens.NUMBER, '1', 1, 3, line, 1, 4),
            ]

    def test_triple_quoted(self):
        input = '''x = """
hello
content
whatisthis""" + "a"\n'''
        s = '''"""
hello
content
whatisthis"""'''
        tks = tokenize(input)
        lines = input.splitlines(True)
        assert tks[:3] == [
            Token(tokens.NAME, 'x', 1, 0, lines[0], 1, 1),
            Token(tokens.EQUAL, '=', 1, 2, lines[0], 1, 3),
            Token(tokens.STRING, s, 1, 4, lines[3], 4, 13),
        ]

    def test_parenthesis_positions(self):
        input = '( ( ( a ) ) ) ( )'
        tks = tokenize(input)[:-3]
        columns = [t.column for t in tks]
        assert columns == [0, 2, 4, 6, 8, 10, 12, 14, 16]
        assert [t.end_column - 1 for t in tks] == columns

    def test_PyCF_DONT_IMPLY_DEDENT(self):
        input = "if 1:\n  1\n"
        # regular mode
        tks = tokenize(input)
        lines = input.splitlines(True)
        del tks[-2] # new parser deletes one newline anyway
        assert tks == [
            Token(tokens.NAME, 'if', 1, 0, lines[0], 1, 2),
            Token(tokens.NUMBER, '1', 1, 3, lines[0], 1, 4),
            Token(tokens.COLON, ':', 1, 4, lines[0], 1, 5),
            Token(tokens.NEWLINE, '', 1, 5, lines[0], -1, -1),
            Token(tokens.INDENT, '  ', 2, 0, lines[1], 2, 2),
            Token(tokens.NUMBER, '1', 2, 2, lines[1], 2, 3),
            Token(tokens.NEWLINE, '', 2, 3, lines[1], -1, -1),
            Token(tokens.DEDENT, '', 2, 0, '', -1, -1),
            Token(tokens.ENDMARKER, '', 2, 0, '', -1, -1),
        ]
        # single mode
        tks = tokenize(input, flags=consts.PyCF_DONT_IMPLY_DEDENT)
        lines = input.splitlines(True)
        del tks[-2] # new parser deletes one newline anyway
        assert tks == [
            Token(tokens.NAME, 'if', 1, 0, lines[0], 1, 2),
            Token(tokens.NUMBER, '1', 1, 3, lines[0], 1, 4),
            Token(tokens.COLON, ':', 1, 4, lines[0], 1, 5),
            Token(tokens.NEWLINE, '', 1, 5, lines[0], -1, -1),
            Token(tokens.INDENT, '  ', 2, 0, lines[1], 2, 2),
            Token(tokens.NUMBER, '1', 2, 2, lines[1], 2, 3),
            Token(tokens.NEWLINE, '', 2, 3, lines[1], -1, -1),
            Token(tokens.ENDMARKER, '', 2, 0, '', -1, -1),
        ]

    def test_ignore_just_linecont(self):
        input = "pass\n    \\\n\npass"
        tks = tokenize(input)
        tps = [tk.token_type for tk in tks]
        assert tps == [tokens.NAME, tokens.NEWLINE, tokens.NAME,
                tokens.NEWLINE, tokens.NEWLINE, tokens.ENDMARKER]

    def test_error_linecont(self):
        check_token_error("a \\ b",
                          "unexpected character after line continuation character",
                          4)

    def test_continuation_and_indentation_levels(self):
        # Make sure the '\` generates indent/dedent tokens
        input1 = r"""\
def fib(n):
    \
'''Print a Fibonacci series up to n.'''
    \
a, b = 0, 1
"""
        input2 = r"""\
def fib(n):
    '''Print a Fibonacci series up to n.'''
    a, b = 0, 1
"""
        def base_eq(tok1, tok2):
            # Line numbers differ because of `\`, so only compare type and value
            return all([(t1.token_type == t2.token_type and t1.value == t2.value) for t1, t2 in zip(tok1, tok2)])
        tks1 = tokenize(input1)
        tks2 = tokenize(input2)
        if not base_eq(tks1, tks2):
            # get better error message
            assert tks1 == tks2

    def test_formfeed1(self):
        # issue gh-5221
        input = "\\\n\ndef(a=1,b:bool=False): pass"
        tks = tokenize(input)
        assert tks[0].token_type != tokens.INDENT

    def test_formfeed2(self):
        # issue gh-5221
        input = "\\\n#\n"
        tks = tokenize(input)
        assert tks[0].token_type != tokens.INDENT

    def test_backslash_before_indent1(self):
        # issue gh-5221
        input1 = r"""\
class AnotherCase:
    '''Some Docstring
    '''"""
        input2 = r"""\
class AnotherCase:
    \
    '''Some Docstring
    '''"""
        tks1 = tokenize(input1)
        tps1 = [tk.token_type for tk in tks1]
        tks2 = tokenize(input2)
        tps2 = [tk.token_type for tk in tks2]
        assert tps1 == tps2

    def test_backslash_before_indent2(self):
        # issue gh-5221
        input1 = r"""\
class Plotter:
\
    pass
"""
        input2 = r"""\
class Plotter:
    pass
"""
        tks1 = tokenize(input1)
        tps1 = [tk.token_type for tk in tks1]
        tks2 = tokenize(input2)
        tps2 = [tk.token_type for tk in tks2]
        assert tps1 == tps2

    def test_error_integers(self):
        check_token_error("0b106",
                "invalid digit '6' in binary literal",
                5)
        check_token_error("0b10_6",
                "invalid digit '6' in binary literal",
                5)
        check_token_error("0b6",
                "invalid digit '6' in binary literal",
                3)
        check_token_error("0b \n",
                "invalid binary literal",
                2)
        check_token_error("0o129",
                "invalid digit '9' in octal literal",
                5)
        check_token_error("0o12_9",
                "invalid digit '9' in octal literal",
                5)
        check_token_error("0o9",
                "invalid digit '9' in octal literal",
                3)
        check_token_error("0o \n",
                "invalid octal literal",
                2)
        check_token_error("0x1__ \n",
                "invalid hexadecimal literal",
                4)
        check_token_error("0x\n",
                "invalid hexadecimal literal",
                2)
        check_token_error("1_ \n",
                "invalid decimal literal",
                2)
        check_token_error("0b1_ \n",
                "invalid binary literal",
                3)
        check_token_error("01212 \n",
                "leading zeros in decimal integer literals are not permitted; use an 0o prefix for octal integers",
                1)
        tokenize("1 2 \n") # does not raise
        tokenize("1 _ \n") # does not raise


    def test_invalid_identifier(self):
        check_token_error("aänc€",
                "invalid character '€' (U+20AC)",
                6)
        check_token_error("a\xc2\xa0b",
                "invalid non-printable character U+00A0",
                2)


class TestTokenizer310Changes(object):
    def test_single_quoted(self):
        check_token_error('s = "abc\n', "unterminated string literal (detected at line 1)", pos=5)

    def test_triple_quoted(self):
        check_token_error('"""abc\n', "unterminated triple-quoted string literal (detected at line 1)")

    def test_single_quoted_detected(self):
        check_token_error('s = "abc\n', "unterminated string literal (detected at line 1)")
        check_token_error('s = "abc\\\na\\\nb\n', "unterminated string literal (detected at line 3)", pos=5)

    def test_triple_quoted_detected(self):
        check_token_error('s = """', "unterminated triple-quoted string literal (detected at line 1)")
        check_token_error('s = """abc\\\na\\\nb\n\n\n\n\n', "unterminated triple-quoted string literal (detected at line 7)")

    def test_warn_number_followed_by_keyword(self):
        line = "0x1for\n"
        tks = tokenize(line)
        assert tks[:-3] == [
            Token(tokens.NUMBER, '0x1f', 1, 0, line, 1, 4),
            Token(tokens.WARNING, 'invalid hexadecimal literal', 1, 0, line),
            Token(tokens.NAME, 'or', 1, 4, line, 1, 6),
            ]

        for line in ("1in 3", "0b01010111and 4", "1 if 0o21231else 2"):
            tks = tokenize(line)
            assert any(tokens.WARNING == tok.token_type for tok in tks)


    def test_error_number_by_non_keyword_name(self):
        check_token_error("1a 2", "invalid decimal literal")

    def test_levels(self):
        line = 'a b (c + d) [[e, f]]'
        tks = tokenize(line)
        levels = [token.level for token in tks]
        assert levels == [0, 0, 1, 1, 1, 1, 0, 1, 2, 2, 2, 2, 1, 0, 0, 0, 0]


# FIXME: Putting the tests inside a class sets up a testspace that
# loads the _bootstrap_external module, which uses f-strings, which
# cannot be parsed by the old parser yet.
# class TestTokenizer312Changes(object):
_fstring_tests = [
    (
        "empty",
        'f""\n',
        [
            (tokens.FSTRING_START, 'f"', 1, 0, 1, 2),
            (tokens.FSTRING_END, '"', 1, 2, 1, 3),
        ],
    ),
    (
        "empty triple",
        'f""""""\n',
        [
            (tokens.FSTRING_START, 'f"""', 1, 0, 1, 4),
            (tokens.FSTRING_END, '"""', 1, 4, 1, 7),
        ],
    ),
    (
        "simple",
        'f"abc"\n',
        [
            (tokens.FSTRING_START, 'f"', 1, 0, 1, 2),
            (tokens.FSTRING_MIDDLE, "abc", 1, 2, 1, 5),
            (tokens.FSTRING_END, '"', 1, 5, 1, 6),
        ],
    ),
    (
        "simple with continuation",
        """f"abc\\
def"
""",
        [
            (tokens.FSTRING_START, 'f"', 1, 0, 1, 2),
            (tokens.FSTRING_MIDDLE, "abc\\\ndef", 1, 2, 2, 3),
            (tokens.FSTRING_END, '"', 2, 3, 2, 4),
        ],
    ),
    (
        "triple multi-line",
        '''f"""\\
abc
def"""
''',
        [
            (tokens.FSTRING_START, 'f"""', 1, 0, 1, 4),
            (tokens.FSTRING_MIDDLE, "\\\nabc\ndef", 1, 4, 3, 3),
            (tokens.FSTRING_END, '"""', 3, 3, 3, 6),
        ],
    ),
    (
        "double brace",
        'f"{{abc}}"\n',
        [
            (tokens.FSTRING_START, 'f"', 1, 0, 1, 2),
            (tokens.FSTRING_MIDDLE, "{abc}", 1, 2, 1, 9),
            (tokens.FSTRING_END, '"', 1, 9, 1, 10),
        ],
    ),
    (
        "simple interpolation",
        'f"x{y}z"\n',
        [
            (tokens.FSTRING_START, 'f"', 1, 0, 1, 2),
            (tokens.FSTRING_MIDDLE, "x", 1, 2, 1, 3),
            (tokens.LBRACE, "{", 1, 3, 1, 4),
            (tokens.NAME, "y", 1, 4, 1, 5),
            (tokens.RBRACE, "}", 1, 5, 1, 6),
            (tokens.FSTRING_MIDDLE, "z", 1, 6, 1, 7),
            (tokens.FSTRING_END, '"', 1, 7, 1, 8),
        ],
    ),
    (
        "quote reuse in interpolation",
        'f"{"x"}"\n',
        [
            (tokens.FSTRING_START, 'f"', 1, 0, 1, 2),
            (tokens.LBRACE, "{", 1, 2, 1, 3),
            (tokens.STRING, '"x"', 1, 3, 1, 6),
            (tokens.RBRACE, "}", 1, 6, 1, 7),
            (tokens.FSTRING_END, '"', 1, 7, 1, 8),
        ],
    ),
    (
        "nested interpolation",
        'f"x{f"y{z}"}"\n',
        [
            (tokens.FSTRING_START, 'f"', 1, 0, 1, 2),
            (tokens.FSTRING_MIDDLE, "x", 1, 2, 1, 3),
            (tokens.LBRACE, "{", 1, 3, 1, 4),
            (tokens.FSTRING_START, 'f"', 1, 4, 1, 6),
            (tokens.FSTRING_MIDDLE, "y", 1, 6, 1, 7),
            (tokens.LBRACE, "{", 1, 7, 1, 8),
            (tokens.NAME, "z", 1, 8, 1, 9),
            (tokens.RBRACE, "}", 1, 9, 1, 10),
            (tokens.FSTRING_END, '"', 1, 10, 1, 11),
            (tokens.RBRACE, "}", 1, 11, 1, 12),
            (tokens.FSTRING_END, '"', 1, 12, 1, 13),
        ],
    ),
    (
        "escaped brace",
        "f'a\\{}'\n",
        [
            (tokens.FSTRING_START, "f'", 1, 0, 1, 2),
            (tokens.FSTRING_MIDDLE, "a\\", 1, 2, 1, 4),
            (tokens.LBRACE, "{", 1, 4, 1, 5),
            (tokens.RBRACE, "}", 1, 5, 1, 6),
            (tokens.FSTRING_END, "'", 1, 6, 1, 7),
        ],
    ),
    (
        "format specifier: date + debug",
        pytest.mark.xfail(
            (
                'f"{today=:%B %d, %Y}"\n',
                [
                    (tokens.FSTRING_START, 'f"', 1, 0, 1, 2),
                    (tokens.LBRACE, "{", 1, 2, 1, 3),
                    (tokens.NAME, "today", 1, 3, 1, 8),
                    (tokens.EQUAL, "=", 1, 8, 1, 9),
                    (tokens.COLON, ":", 1, 9, 1, 10),
                    (tokens.FSTRING_MIDDLE, "%B %d, %Y", 1, 10, 1, 24),
                    (tokens.RBRACE, "}", 1, 24, 1, 25),
                    (tokens.FSTRING_END, '"', 1, 25, 1, 26),
                ],
            ),
            reason="TODO",
        ),
    ),
    (
        "format specifier: interpolation",
        pytest.mark.xfail(
            (
                'f"result: {value:{width}.{precision}}"\n',
                [
                    (tokens.FSTRING_START, 'f"', 1, 0, 1, 2),
                    (tokens.FSTRING_MIDDLE, "result: ", 1, 2, 1, 10),
                    (tokens.LBRACE, "{", 1, 10, 1, 11),
                    (tokens.NAME, "value", 1, 11, 1, 16),
                    (tokens.COLON, ":", 1, 16, 1, 17),
                    (tokens.LBRACE, "{", 1, 17, 1, 18),
                    (tokens.NAME, "width", 1, 18, 1, 23),
                    (tokens.RBRACE, "}", 1, 23, 1, 24),
                    (tokens.FSTRING_MIDDLE, ".", 1, 24, 1, 25),
                    (tokens.LBRACE, "{", 1, 25, 1, 26),
                    (tokens.NAME, "precision", 1, 26, 1, 35),
                    (tokens.RBRACE, "}", 1, 35, 1, 36),
                    (tokens.RBRACE, "}", 1, 36, 1, 37),
                    (tokens.FSTRING_END, '"', 1, 37, 1, 38),
                ],
            ),
            reason="TODO",
        ),
    ),
    (
        "format specifier: funky ending",
        pytest.mark.xfail(
            (
                'f"{:"}\n',
                [
                    (tokens.FSTRING_START, 'f"', 1, 0, 1, 2),
                    (tokens.LBRACE, "{", 1, 2, 1, 3),
                    (tokens.COLON, ":", 1, 3, 1, 4),
                    (tokens.FSTRING_END, '"', 1, 4, 1, 5),
                    (tokens.RBRACE, "}", 1, 5, 1, 6),
                ],
            ),
            reason="TODO",
        ),
    ),
    (
        "format specifier: double braces",
        pytest.mark.xfail(
            (
                'f"{x:{{}}b"}\n',
                [
                    (tokens.FSTRING_START, 'f"', 1, 0, 1, 2),
                    (tokens.LBRACE, "{", 1, 2, 1, 3),
                    (tokens.NAME, "x", 1, 3, 1, 4),
                    (tokens.COLON, ":", 1, 4, 1, 5),
                    (tokens.LBRACE, "{", 1, 5, 1, 6),
                    (tokens.LBRACE, "{", 1, 6, 1, 7),
                    (tokens.RBRACE, "}", 1, 7, 1, 8),
                    (tokens.RBRACE, "}", 1, 8, 1, 9),
                    (tokens.FSTRING_MIDDLE, "b", 1, 9, 1, 10),
                    (tokens.FSTRING_END, '"', 1, 10, 1, 11),
                    (tokens.RBRACE, "}", 1, 11, 1, 12),
                ],
            ),
            reason="TODO",
        ),
    ),
    (
        "format specifier: newline",
        pytest.mark.xfail(
            (
                'f"{x:y\nz}w"\n',
                [
                    (tokens.FSTRING_START, 'f"', 1, 0, 1, 2),
                    (tokens.LBRACE, "{", 1, 2, 1, 3),
                    (tokens.NAME, "x", 1, 3, 1, 4),
                    (tokens.COLON, ":", 1, 4, 1, 5),
                    (tokens.FSTRING_MIDDLE, "y", 1, 5, 1, 6),
                    (tokens.NEWLINE, "\n", 1, 6, -1, -1),
                    (tokens.NAME, "z", 2, 0, 2, 1),
                    (tokens.RBRACE, "}", 2, 1, 2, 2),
                    (tokens.FSTRING_MIDDLE, "w", 2, 2, 2, 3),
                    (tokens.FSTRING_END, '"', 2, 3, 2, 4),
                ],
            ),
            reason="TODO",
        ),
    ),
    (
        "format specifier: continuation",
        pytest.mark.xfail(
            (
                'f"{x:y\\\nz}"\n',
                [
                    (tokens.FSTRING_START, 'f"', 1, 0, 1, 2),
                    (tokens.LBRACE, "{", 1, 2, 1, 3),
                    (tokens.NAME, "x", 1, 3, 1, 4),
                    (tokens.COLON, ":", 1, 4, 1, 5),
                    (tokens.FSTRING_MIDDLE, "y\\\nz", 1, 5, 2, 1),
                    (tokens.RBRACE, "}", 2, 1, 2, 2),
                    (tokens.FSTRING_END, '"', 2, 2, 2, 3),
                ],
            ),
            reason="TODO",
        ),
    ),
]

@pytest.mark.parametrize(
    "source, expected",
    [t[1] if len(t) == 2 else t[1:] for t in _fstring_tests],
    ids=[t[0] for t in _fstring_tests],
)
def test_f_string(source, expected):
    lines = source.splitlines(True)
    tks = tokenize(source)
    assert tks[: len(expected)] == [
        Token(
            tk_type,
            value,
            lineno,
            col_offset,
            lines[end_lineno - 1],
            end_lineno,
            end_col_offset,
        )
        for tk_type, value, lineno, col_offset, end_lineno, end_col_offset in expected
    ]

_fstring_error_tests = [
    (
        "single closing brace",
        'f"abc}def"\n',
        "f-string: single '}' is not allowed",
        6,
        1,
    ),
    # TODO: The 'pos' values here are after the f-string start token
    #  while on CPython they come before it.
    (
        "unterminated f-string",
        'f"abc\n',
        "unterminated f-string literal (detected at line 1)",
        3,
        1,
    ),
    (
        "unterminated f-string after continuation",
        '''f"abc\\
def
''',
        "unterminated f-string literal (detected at line 2)",
        3,
        1,
    ),
    (
        "unterminated f-string triple",
        '''f"""abc\n''',
        "unterminated triple-quoted f-string literal (detected at line 1)",
        5,
        1,
    ),
]


@pytest.mark.parametrize(
    "source, msg, pos, line",
    [t[1:] for t in _fstring_error_tests],
    ids=[t[0] for t in _fstring_error_tests],
)
def test_f_string_errors(source, msg, pos, line):
    check_token_error(source, msg, pos, line)

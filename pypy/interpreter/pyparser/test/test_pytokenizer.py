from pypy.interpreter.pyparser.pythonlexer import Source, TokenError, \
     match_encoding_declaration
from pypy.interpreter.pyparser.grammar import Token, GrammarElement
from pypy.interpreter.pyparser.pythonparse import make_pyparser

P = make_pyparser('2.4')

EQUAL = P.tokens['EQUAL']
ENDMARKER = P.tokens['ENDMARKER']
LSQB = P.tokens['LSQB']
MINUS = P.tokens['MINUS']
NAME = P.tokens['NAME']
NEWLINE = P.tokens['NEWLINE']
NULLTOKEN = P.tokens['NULLTOKEN']
NUMBER = P.tokens['NUMBER']
RSQB = P.tokens['RSQB']
STRING = P.tokens['STRING']

def parse_source(source):
    """returns list of parsed tokens"""
    lexer = Source( P, source.splitlines(True), {})
    tokens = []
    last_token = Token( P, NULLTOKEN, None)
    while last_token.codename != ENDMARKER:
        last_token = lexer.next()
        tokens.append(last_token)
    return tokens

## class TestSuite:
##     """Tokenizer test suite"""
PUNCTS = [
    # Here should be listed each existing punctuation
    '>=', '<>', '!=', '<', '>', '<=', '==', '*=',
    '//=', '%=', '^=', '<<=', '**=', '|=',
    '+=', '>>=', '=', '&=', '/=', '-=', ',', '^',
    '>>', '&', '+', '*', '-', '/', '.', '**',
    '%', '<<', '//', '|', ')', '(', ';', ':',
    '@',
    '[', ']', '`', '{', '}',
    ]

NUMBERS = [
    # Here should be listed each different form of number
    '1', '1.23', '1.', '0',
    '1L', '1l',
    '0x12L', '0x12l', '0X12', '0x12',
    '1j', '1J',
    '1e2', '1.2e4',
    '0.1', '0.', '0.12', '.2',
    ]

BAD_NUMBERS = [
    'j', '0xg', '0xj', '0xJ',
    ]

def test_several_lines_list():
    """tests list definition on several lines"""
    s = """['a'
    ]"""
    tokens = parse_source(s)
    assert tokens[:4] == [Token(P, LSQB, None), Token(P, STRING, "'a'"),
                          Token(P, RSQB, None), Token(P, NEWLINE, '')]

def test_numbers():
    """make sure all kind of numbers are correctly parsed"""
    for number in NUMBERS:
        assert parse_source(number)[0] == Token(P, NUMBER, number)
        neg = '-%s' % number
        assert parse_source(neg)[:2] == [Token(P, MINUS, None), 
                                         Token(P, NUMBER, number)]
    for number in BAD_NUMBERS:
        assert parse_source(number)[0] != Token(P, NUMBER, number)

def test_hex_number():
    """basic pasrse"""
    tokens = parse_source("a = 0x12L")
    assert tokens[:4] == [Token(P, NAME, 'a'), Token(P, EQUAL, None),
                          Token(P, NUMBER, '0x12L'), Token(P, NEWLINE, '')]

def test_punct():
    """make sure each punctuation is correctly parsed"""
    for pstr in PUNCTS:
        if   pstr == ')': prefix = '('
        elif pstr == ']': prefix = '['
        elif pstr == '}': prefix = '{'
        else:             prefix = ''
        try:
            tokens = parse_source(prefix+pstr)
        except TokenError, error:
            tokens = [tok for tok, _, _, _ in error.token_stack]
        if prefix:
            tokens.pop(0)
        assert tokens[0].codename == P.tok_values[pstr]


def test_encoding_declarations_match():
    checks = [
        ('# -*- coding: ISO-8859-1 -*-', 'ISO-8859-1'),
        ('# -*- coding: ISO-8859-1 -*-\n', 'ISO-8859-1'),
        ('# -*- coding: ISO-8859-1', 'ISO-8859-1'),
        ('# -*- coding= UTF-8', 'UTF-8'),
        ('#  coding= UTF-8', 'UTF-8'),
        ('#  coding= UTF-8 hello', 'UTF-8'),
        ('# -*- coding: ISO_8859-1', 'ISO_8859-1'),
        ('# -*- coding ISO_8859-1', None),
        ('# coding ISO_8859-1', None),
        ]
    for comment, encoding in checks:
        res = match_encoding_declaration(comment)
        assert res == encoding, "Failed on (%s), %s != %s" % (comment, res, encoding)

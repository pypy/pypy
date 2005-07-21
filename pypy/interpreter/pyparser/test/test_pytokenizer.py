from pypy.interpreter.pyparser.pythonlexer import Source, TokenError, \
     match_encoding_declaration
from pypy.interpreter.pyparser.grammar import Token, GrammarElement
from pypy.interpreter.pyparser.pytoken import EQUAL, ENDMARKER, LSQB, MINUS, NAME, NEWLINE, NULLTOKEN, NUMBER, RSQB, STRING

from pypy.interpreter.pyparser.pytoken import tok_name, tok_punct
GrammarElement.symbols = tok_name


def parse_source(source):
    """returns list of parsed tokens"""
    lexer = Source(source.splitlines(True))
    tokens = []
    last_token = Token(NULLTOKEN, None)
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
    # '@', # XXX This one is skipped for now (?!)
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
    assert tokens == [Token(LSQB, None), Token(STRING, "'a'"),
                      Token(RSQB, None), Token(NEWLINE, ''),
                      Token(ENDMARKER, '')]

def test_numbers():
    """make sure all kind of numbers are correctly parsed"""
    for number in NUMBERS:
        assert parse_source(number)[0] == Token(NUMBER, number)
        neg = '-%s' % number
        assert parse_source(neg)[:2] == [Token(MINUS, None), 
                                         Token(NUMBER, number)]
    for number in BAD_NUMBERS:
        assert parse_source(number)[0] != Token(NUMBER, number)

def test_hex_number():
    """basic pasrse"""
    tokens = parse_source("a = 0x12L")
    assert tokens == [Token(NAME, 'a'), Token(EQUAL, None),
                      Token(NUMBER, '0x12L'), Token(NEWLINE, ''),
                      Token(ENDMARKER, '')]

def test_punct():
    """make sure each punctuation is correctly parsed"""
    for pstr in PUNCTS:
        try:
            tokens = parse_source(pstr)
        except TokenError, error:
            tokens = [tok for tok, _, _, _ in error.token_stack]
        assert tokens[0].codename == tok_punct[pstr]


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

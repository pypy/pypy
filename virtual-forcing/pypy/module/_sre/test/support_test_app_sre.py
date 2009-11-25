"""Support functions for app-level _sre tests."""
import locale, _sre
from sre_constants import OPCODES, ATCODES, CHCODES

def encode_literal(string):
    opcodes = []
    for character in string:
        opcodes.extend([OPCODES["literal"], ord(character)])
    return opcodes

def assert_match(opcodes, strings):
    assert_something_about_match(lambda x: x, opcodes, strings)

def assert_no_match(opcodes, strings):
    assert_something_about_match(lambda x: not x, opcodes, strings)

def assert_something_about_match(assert_modifier, opcodes, strings):
    if isinstance(strings, str):
        strings = [strings]
    for string in strings:
        assert assert_modifier(search(opcodes, string))

def search(opcodes, string):
    pattern = _sre.compile("ignore", 0, opcodes, 0, {}, None)
    return pattern.search(string)

def void_locale():
    locale.setlocale(locale.LC_ALL, (None, None))

def assert_lower_equal(tests, flags):
    for arg, expected in tests:
        assert ord(expected) == _sre.getlower(ord(arg), flags)

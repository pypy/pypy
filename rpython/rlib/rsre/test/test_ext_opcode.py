"""
Test for cases that cannot be produced using the Python 2.7 sre_compile
module, but can be produced by other means (e.g. Python 3.5)
"""

from rpython.rlib.rsre import rsre_core, rsre_constants
from rpython.rlib.rsre.rsre_char import MAXREPEAT
from rpython.rlib.rsre.test.support import match, Position

# import OPCODE_XX as XX
for name, value in rsre_constants.__dict__.items():
    if name.startswith('OPCODE_') and isinstance(value, int):
        globals()[name[7:]] = value


def test_repeat_one_with_backref():
    # Python 3.5 compiles "(.)\1*" using REPEAT_ONE instead of REPEAT:
    # it's a valid optimization because \1 is always one character long
    r = [MARK, 0, ANY, MARK, 1, REPEAT_ONE, 6, 0, MAXREPEAT, 
         GROUPREF, 0, SUCCESS, SUCCESS]
    assert rsre_core.match(rsre_core.CompiledPattern(r, 0), "aaa").match_end == 3

def test_min_repeat_one_with_backref():
    # Python 3.5 compiles "(.)\1*?b" using MIN_REPEAT_ONE
    r = [MARK, 0, ANY, MARK, 1, MIN_REPEAT_ONE, 6, 0, MAXREPEAT,
         GROUPREF, 0, SUCCESS, LITERAL, 98, SUCCESS]
    assert rsre_core.match(rsre_core.CompiledPattern(r, 0), "aaab").match_end == 4

def test_possessive_repeat_one():
    r = [POSSESSIVE_REPEAT_ONE, 6, 0, MAXREPEAT, LITERAL, ord('a'), SUCCESS, LITERAL, ord('b'), SUCCESS]
    assert rsre_core.match(rsre_core.CompiledPattern(r, 0), "aaab").match_end == 4
    r = [POSSESSIVE_REPEAT_ONE, 6, 0, MAXREPEAT, LITERAL, ord('a'), SUCCESS, LITERAL, ord('a'), SUCCESS]
    assert rsre_core.match(rsre_core.CompiledPattern(r, 0), "aaaa") is None

def test_possessive_repeat():
    r = [POSSESSIVE_REPEAT, 8, 0, MAXREPEAT, LITERAL, ord('a'), LITERAL, ord('b'), SUCCESS, LITERAL, ord('b'), LITERAL, ord('b'), SUCCESS]
    assert rsre_core.match(rsre_core.CompiledPattern(r, 0), "abababababbb").match_end == 12
    r = [POSSESSIVE_REPEAT, 8, 0, MAXREPEAT, LITERAL, ord('a'), LITERAL, ord('b'), SUCCESS, LITERAL, ord('a'), LITERAL, ord('b'), SUCCESS]
    assert rsre_core.match(rsre_core.CompiledPattern(r, 0), "abababababababab") is None

def test_atomic_group():
    r = [ATOMIC_GROUP, 11, LITERAL, ord('a'), REPEAT_ONE, 6, 0, 1, LITERAL, ord('b'), SUCCESS, SUCCESS, LITERAL, ord('b'), SUCCESS]
    assert rsre_core.match(rsre_core.CompiledPattern(r, 0), "abb").match_end == 3
    assert rsre_core.match(rsre_core.CompiledPattern(r, 0), "ab") is None

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

ab_plus_plus_bb = [POSSESSIVE_REPEAT, 7, 0, MAXREPEAT, LITERAL, ord('a'), LITERAL, ord('b'), SUCCESS, LITERAL, ord('b'), LITERAL, ord('b'), SUCCESS]

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
    r = ab_plus_plus_bb
    assert rsre_core.match(rsre_core.CompiledPattern(r, 0), "abababababbb").match_end == 12
    r = [POSSESSIVE_REPEAT, 7, 0, MAXREPEAT, LITERAL, ord('a'), LITERAL, ord('b'), SUCCESS, LITERAL, ord('a'), LITERAL, ord('b'), SUCCESS]
    assert rsre_core.match(rsre_core.CompiledPattern(r, 0), "abababababababab") is None
    r = [POSSESSIVE_REPEAT, 7, 0, MAXREPEAT, LITERAL, ord('a'), LITERAL, ord('b'), SUCCESS, LITERAL, ord('c'), SUCCESS]
    assert rsre_core.match(rsre_core.CompiledPattern(r, 0), "ababababababababc") is not None
    assert rsre_core.match(rsre_core.CompiledPattern(r, 0), "ababababababababc", fullmatch=True) is not None

def test_atomic_group():
    r = [ATOMIC_GROUP, 11, LITERAL, ord('a'), REPEAT_ONE, 6, 0, 1, LITERAL, ord('b'), SUCCESS, SUCCESS, LITERAL, ord('b'), SUCCESS]
    assert rsre_core.match(rsre_core.CompiledPattern(r, 0), "abb").match_end == 3
    assert rsre_core.match(rsre_core.CompiledPattern(r, 0), "ab") is None

def test_atomic_group_fullmatch_bug():
    r = [ATOMIC_GROUP, 4, LITERAL, ord('t'), SUCCESS, LITERAL, ord('a'), SUCCESS]
    assert rsre_core.match(rsre_core.CompiledPattern(r, 0), "ta") is not None
    assert rsre_core.match(rsre_core.CompiledPattern(r, 0), "ta", fullmatch=True) is not None

def test_possessive_repeat_of_atomic_group():
    # (?>x)++x
    r = [POSSESSIVE_REPEAT, 8, 1, MAXREPEAT, ATOMIC_GROUP, 4, LITERAL, ord('x'), SUCCESS, SUCCESS, LITERAL, ord('x'), SUCCESS]
    assert rsre_core.match(rsre_core.CompiledPattern(r, 0), "xxx") is None
    # '(?>x++)x'
    r = [ATOMIC_GROUP, 9, POSSESSIVE_REPEAT, 6, 1, MAXREPEAT, LITERAL, ord('x'), SUCCESS, SUCCESS, LITERAL, ord('x'), SUCCESS]
    assert rsre_core.match(rsre_core.CompiledPattern(r, 0), "xxx") is None

def test_possessive_repeat_mark():
    # '(.)++.'
    r = [POSSESSIVE_REPEAT, 8, 1, MAXREPEAT, MARK, 0, ANY, MARK, 1, SUCCESS, ANY, SUCCESS]
    assert rsre_core.match(rsre_core.CompiledPattern(r, 0), "xxx") is None

def test_possesive_repeat_groups():
    # (.){3}+
    r = [POSSESSIVE_REPEAT, 8, 3, 3, MARK, 0, ANY, MARK, 1, SUCCESS, SUCCESS]
    match = rsre_core.match(rsre_core.CompiledPattern(r, 0), "abc")
    assert match.match_marks is not None

def test_possessive_repeat_zero_width():
    # (e?){2,4}+a
    r = [POSSESSIVE_REPEAT, 14, 2, 4, MARK, 0, REPEAT_ONE, 6, 0, 1, LITERAL, ord('e'), SUCCESS, MARK, 1, SUCCESS, LITERAL, ord('a'), SUCCESS]
    match = rsre_core.match(rsre_core.CompiledPattern(r, 0), "eeea")
    assert match.match_marks is not None

"""
Test for cases that cannot be produced using the Python 2.7 sre_compile
module, but can be produced by other means (e.g. Python 3.5)
"""

import pytest

from rpython.rlib.rsre import rsre_core, rsre_constants, rsre_utf8
from rpython.rlib.rsre.rsre_char import MAXREPEAT
from rpython.rlib.rsre.test.support import match, Position

# import OPCODE_XX as XX
for name, value in rsre_constants.__dict__.items():
    if name.startswith('OPCODE_') and isinstance(value, int):
        globals()[name[7:]] = value

ab_plus_plus_bb = [POSSESSIVE_REPEAT, 7, 0, MAXREPEAT, LITERAL, ord('a'), LITERAL, ord('b'), SUCCESS, LITERAL, ord('b'), LITERAL, ord('b'), SUCCESS]

@pytest.mark.parametrize('opcode', [REPEAT_ONE, MIN_REPEAT_ONE,
                                    POSSESSIVE_REPEAT_ONE])
@pytest.mark.parametrize('too_short', [False, True])
def test_repeat_one_utf8_rejects_before_boundary_walk(opcode, too_short,
                                                    monkeypatch):
    # No INFO block: exercise the repeat's own checks, including at an offset.
    code = rsre_core.CompiledPattern(
        [opcode, 6, 256, 512, LITERAL, ord('x'), SUCCESS, SUCCESS], 0)

    def unexpected_walk(*args):
        raise AssertionError('walked the minimum repetition boundary')

    monkeypatch.setattr(rsre_utf8.Utf8MatchContext, 'next_n', unexpected_walk)
    if too_short:
        def unexpected_read(*args):
            raise AssertionError('read input too short for the repeat')
        monkeypatch.setattr(rsre_utf8.Utf8MatchContext, 'str', unexpected_read)
        text = 'x' * 16
    else:
        text = 'a' * 512
    for start in (0, 1):
        assert rsre_utf8.utf8match(code, text, start) is None

@pytest.mark.parametrize('opcode', [REPEAT_ONE, MIN_REPEAT_ONE,
                                    POSSESSIVE_REPEAT_ONE])
def test_repeat_one_utf8_minimum_and_backtracking(opcode):
    code = rsre_core.CompiledPattern(
        [opcode, 6, 2, 3, LITERAL, 0xe9, SUCCESS,
         LITERAL, 0xe9, SUCCESS], 0)
    char = u'\xe9'.encode('utf-8')
    for count in range(5):
        result = rsre_utf8.utf8match(code, char * count)
        if count < 3 or (opcode == POSSESSIVE_REPEAT_ONE and count == 3):
            assert result is None
        else:
            expected = 3 if opcode == MIN_REPEAT_ONE else min(count, 4)
            assert result.span() == (0, 2 * expected)

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

def test_possessive_repeat_one_min_count():
    # x++ (min=1): match must fail when the starting position has zero
    # repetitions, even though the tail (SUCCESS) would accept zero chars.
    # Regression test for missing "if ptr < minptr: return" guard.
    r = [POSSESSIVE_REPEAT_ONE, 5, 1, MAXREPEAT, LITERAL, ord('x'), SUCCESS, SUCCESS]
    # 'axx' - position 0 has no 'x', so match at 0 must fail
    assert rsre_core.match(rsre_core.CompiledPattern(r, 0), "axx") is None
    # search must skip position 0 and find the run at position 1
    ctx = rsre_core.search(rsre_core.CompiledPattern(r, 0), "axx")
    assert ctx is not None
    assert ctx.match_start == 1
    assert ctx.match_end == 3
    # 'xx' at position 0 - match must succeed consuming both chars
    assert rsre_core.match(rsre_core.CompiledPattern(r, 0), "xx").match_end == 2

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

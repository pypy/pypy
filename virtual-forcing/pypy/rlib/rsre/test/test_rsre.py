"""Interp-level rsre tests."""
import sys
from py.test import raises
from pypy.rlib.rsre.rsre import SimpleStringState, set_unicode_db
from pypy.rlib.rsre import rsre_char
isre = SimpleStringState.rsre_core

from pypy.module.unicodedata import unicodedb_3_2_0
set_unicode_db(unicodedb_3_2_0)

EM_SPACE = u"\u2001"
INDIAN_DIGIT = u"\u0966"

def create_context(string, string_position, end):
    state = SimpleStringState(string, 0, end)
    state.string_position = string_position
    return state._MatchContext(state, [])

def test_is_uni_linebreak():
    for char in ["\n", "\r"]:
        assert rsre_char.is_uni_linebreak(ord(char))
    for char in [" ", "b"]:
        assert not rsre_char.is_uni_linebreak(ord(char))
    assert rsre_char.is_uni_linebreak(8232)

def test_is_uni_word():
    for char in ["a", "_", "\xe4"]:
        assert rsre_char.is_uni_word(ord(char))
    for char in ["a", "_", "\xe4", u"\u00e4", u"\u03a0"]:
        assert rsre_char.is_uni_word(ord(char))
    for char in [".", " "]:
        assert not rsre_char.is_uni_word(ord(char))
    for char in [".", " ", EM_SPACE]:
        assert not rsre_char.is_uni_word(ord(char))

def test_is_loc_word():
    # should also test chars actually affected by locale (between 128 and 256)
    for char in ["1", "2"]:
        assert rsre_char.is_loc_word(ord(char))
        assert rsre_char.is_loc_word(ord(char))
    for char in [" ", u".", u"\u03a0"]:
        assert not rsre_char.is_loc_word(ord(char))

def test_is_uni_digit():
    for char in ["0", "9"]:
        assert rsre_char.is_uni_digit(ord(char))
    for char in ["0", "9", INDIAN_DIGIT]:
        assert rsre_char.is_uni_digit(ord(char))
    for char in [" ", "s"]:
        assert not rsre_char.is_uni_digit(ord(char))

def test_is_uni_space():
    for char in [" ", "\t"]:
        assert rsre_char.is_uni_space(ord(char))
    for char in ["\v", "\n", EM_SPACE]:
        assert rsre_char.is_uni_space(ord(char))
    for char in ["a", "1"]:
        assert not rsre_char.is_uni_space(ord(char))

def test_at_beginning():
    assert isre.at_beginning(create_context("", 0, 0))
    assert not isre.at_beginning(create_context("a", 1, 1))

def test_at_beginning_line():
    assert isre.at_beginning_line(create_context("", 0, 0))
    assert isre.at_beginning_line(create_context("\na", 1, 3))
    assert not isre.at_beginning_line(create_context("a", 1, 2))

def test_at_end():
    for string, pos, end in [("", 0, 0), ("a", 1, 1), ("a\n", 1, 2)]:
        assert isre.at_end(create_context(string, pos, end))
    assert not isre.at_end(create_context("a", 0, 1))

def test_at_boundary():
    for string, pos, end in [("a.", 1, 2), (".a", 1, 2)]:
        assert isre.at_boundary(create_context(string, pos, end))
    for string, pos, end in [(".", 0, 1), (".", 1, 1), ("ab", 1, 2)]:
        assert not isre.at_boundary(create_context(string, pos, end))

def test_getlower():
    assert rsre_char.getlower(ord("A"), 0) == ord("a")

def test_SimpleStringState():
    state = SimpleStringState("A", 0, -1)
    assert state.get_char_ord(0) == ord("A")
    assert state.lower(state.get_char_ord(0)) == ord("a")

def test_get_byte_array():
    if sys.byteorder == "big":
        if rsre_char.CODESIZE == 2:
            assert [0, 1] == rsre_char.to_byte_array(1)
            assert [1, 0] == rsre_char.to_byte_array(256)
            assert [1, 2] == rsre_char.to_byte_array(258)
        else:
            assert [0, 0, 0, 1] == rsre_char.to_byte_array(1)
            assert [0, 0, 1, 0] == rsre_char.to_byte_array(256)
            assert [1, 2, 3, 4] == rsre_char.to_byte_array(0x01020304)
    else:
        if rsre_char.CODESIZE == 2:
            assert [1, 0] == rsre_char.to_byte_array(1)
            assert [0, 1] == rsre_char.to_byte_array(256)
            assert [2, 1] == rsre_char.to_byte_array(258)
        else:
            assert [1, 0, 0, 0] == rsre_char.to_byte_array(1)
            assert [0, 1, 0, 0] == rsre_char.to_byte_array(256)
            assert [4, 3, 2, 1] == rsre_char.to_byte_array(0x01020304)

# ____________________________________________________________
#
# XXX no matching/searching tests here, they are in pypy/module/_sre for now

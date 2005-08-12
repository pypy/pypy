"""Interp-level _sre tests."""
import autopath
from py.test import raises
import pypy.module._sre.interp_sre as isre

EM_SPACE = u"\u2001"
INDIAN_DIGIT = u"\u0966"

def test_is_uni_linebreak(space):
    for char in ["\n", "\r"]:
        assert isre.is_uni_linebreak(space, space.wrap(char))
        assert isre.is_uni_linebreak(space, space.newunicode([ord(char)]))
    for char in [" ", "b"]:
        assert not isre.is_uni_linebreak(space, space.wrap(char))
        assert not isre.is_uni_linebreak(space, space.newunicode([ord(char)]))
    assert isre.is_uni_linebreak(space, space.newunicode([8232]))

def test_is_uni_word(space):
    for char in ["a", "_", "\xe4"]:
        assert isre.is_uni_word(space, space.wrap(char))
    for char in ["a", "_", "\xe4", u"\u00e4", u"\u03a0"]:
        assert isre.is_uni_word(space, space.newunicode([ord(char)]))
    for char in [".", " "]:
        assert not isre.is_uni_word(space, space.wrap(char))
    for char in [".", " ", EM_SPACE]:
        assert not isre.is_uni_word(space, space.newunicode([ord(char)]))

def test_is_loc_word(space):
    # should also test chars actually affected by locale (between 128 and 256)
    for char in ["1", "2"]:
        assert isre.is_loc_word(space, space.wrap(char))
        assert isre.is_loc_word(space, space.newunicode([ord(char)]))
    for char in [" ", u".", u"\u03a0"]:
        assert not isre.is_loc_word(space, space.newunicode([ord(char)]))

def test_is_uni_digit(space):
    for char in ["0", "9"]:
        assert isre.is_uni_digit(space, space.wrap(char))
    for char in ["0", "9", INDIAN_DIGIT]:
        assert isre.is_uni_digit(space, space.newunicode([ord(char)]))
    for char in [" ", "s"]:
        assert not isre.is_uni_digit(space, space.wrap(char))

def test_is_uni_space(space):
    for char in [" ", "\t"]:
        assert isre.is_uni_space(space, space.wrap(char))
    for char in ["\v", "\n", EM_SPACE]:
        assert isre.is_uni_space(space, space.newunicode([ord(char)]))
    for char in ["a", "1"]:
        assert not isre.is_uni_space(space, space.wrap(char))

def test_at_beginning(space):
    assert isre.at_beginning(space,
                            isre.MatchContext(space, [], space.wrap(""), 0, 0))
    assert not isre.at_beginning(space,
                            isre.MatchContext(space, [], space.wrap("a"), 1, 1))

def test_at_beginning_line(space):
    assert isre.at_beginning_line(space,
                            isre.MatchContext(space, [], space.wrap(""), 0, 0))
    assert isre.at_beginning_line(space,
                            isre.MatchContext(space, [], space.wrap("\na"), 1, 3))
    assert not isre.at_beginning_line(space,
                            isre.MatchContext(space, [], space.wrap("a"), 1, 2))

def test_at_end(space):
    for string, pos, end in [("", 0, 0), ("a", 1, 1), ("a\n", 1, 2)]:
        assert isre.at_end(space,
                        isre.MatchContext(space, [], space.wrap(string), pos, end))
    assert not isre.at_end(space,
                            isre.MatchContext(space, [], space.wrap("a"), 0, 1))

def test_at_boundary(space):
    for string, pos, end in [("a.", 1, 2), (".a", 1, 2)]:
        assert isre.at_boundary(space,
                        isre.MatchContext(space, [], space.wrap(string), pos, end))
    for string, pos, end in [(".", 0, 1), (".", 1, 1), ("ab", 1, 2)]:
        assert not isre.at_boundary(space,
                        isre.MatchContext(space, [], space.wrap(string), pos, end))

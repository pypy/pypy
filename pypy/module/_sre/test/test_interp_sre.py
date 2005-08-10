"""Interp-level _sre tests."""
import autopath
from py.test import raises
import pypy.module._sre.interp_sre as isre

EM_SPACE = u"\u2001"
INDIAN_DIGIT = u"\u0966"

def test_is_uni_linebreak(space):
    for char in ["\n", "\r"]:
        assert space.is_true(isre.is_uni_linebreak(space, space.wrap(char)))
        assert space.is_true(isre.is_uni_linebreak(space, space.newunicode([ord(char)])))
    for char in [" ", "b"]:
        assert not space.is_true(isre.is_uni_linebreak(space, space.wrap(char)))
        assert not space.is_true(isre.is_uni_linebreak(space, space.newunicode([ord(char)])))
    assert space.is_true(isre.is_uni_linebreak(space, space.newunicode([8232])))

def test_is_uni_word(space):
    for char in ["a", "_", "\xe4"]:
        assert space.is_true(isre.is_uni_word(space, space.wrap(char)))
    for char in ["a", "_", "\xe4", u"\u00e4", u"\u03a0"]:
        assert space.is_true(isre.is_uni_word(space, space.newunicode([ord(char)])))
    for char in [".", " "]:
        assert not space.is_true(isre.is_uni_word(space, space.wrap(char)))
    for char in [".", " ", EM_SPACE]:
        assert not space.is_true(isre.is_uni_word(space, space.newunicode([ord(char)])))

def test_is_loc_word(space):
    # should also test chars actually affected by locale (between 128 and 256)
    for char in ["1", "2"]:
        assert space.is_true(isre.is_loc_word(space, space.wrap(char)))
        assert space.is_true(isre.is_loc_word(space, space.newunicode([ord(char)])))
    for char in [" ", u".", u"\u03a0"]:
        assert not space.is_true(isre.is_loc_word(space, space.newunicode([ord(char)])))

def test_is_uni_digit(space):
    for char in ["0", "9"]:
        assert space.is_true(isre.is_uni_digit(space, space.wrap(char)))
    for char in ["0", "9", INDIAN_DIGIT]:
        assert space.is_true(isre.is_uni_digit(space, space.newunicode([ord(char)])))
    for char in [" ", "s"]:
        assert not space.is_true(isre.is_uni_digit(space, space.wrap(char)))

def test_is_uni_space(space):
    for char in [" ", "\t"]:
        assert space.is_true(isre.is_uni_space(space, space.wrap(char)))
    for char in ["\v", "\n", EM_SPACE]:
        assert space.is_true(isre.is_uni_space(space, space.newunicode([ord(char)])))
    for char in ["a", "1"]:
        assert not space.is_true(isre.is_uni_space(space, space.wrap(char)))

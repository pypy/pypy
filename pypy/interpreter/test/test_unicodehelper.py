import pytest
try:
    from hypothesis import given, strategies
    HAS_HYPOTHESIS = True
except ImportError:
    HAS_HYPOTHESIS = False
import struct
import sys

from rpython.rlib import rutf8

from pypy.interpreter.unicodehelper import str_decode_utf8
from pypy.interpreter.unicodehelper import utf8_encode_ascii, str_decode_ascii
from pypy.interpreter import unicodehelper as uh
from pypy.module._codecs.interp_codecs import CodecState

def decode_utf8(u):
    return str_decode_utf8(u, True, "strict", None)

def test_decode_utf8():
    assert decode_utf8("abc") == ("abc", 3, 3)
    assert decode_utf8("\xe1\x88\xb4") == ("\xe1\x88\xb4", 3, 1)
    assert decode_utf8("\xed\xa0\x80") == ("\xed\xa0\x80", 3, 1)
    assert decode_utf8("\xed\xb0\x80") == ("\xed\xb0\x80", 3, 1)
    assert decode_utf8("\xed\xa0\x80\xed\xb0\x80") == (
        "\xed\xa0\x80\xed\xb0\x80", 6, 2)
    assert decode_utf8("\xf0\x90\x80\x80") == ("\xf0\x90\x80\x80", 4, 1)

def test_utf8_encode_ascii():
    assert utf8_encode_ascii("abc", "??", "??") == "abc"
    def eh(errors, encoding, reason, p, start, end):
        lst.append((errors, encoding, p, start, end))
        return "<FOO>", end
    lst = []
    input = u"\u1234".encode("utf8")
    assert utf8_encode_ascii(input, "??", eh) == "<FOO>"
    assert lst == [("??", "ascii", input, 0, 1)]
    lst = []
    input = u"\u1234\u5678abc\u8765\u4321".encode("utf8")
    assert utf8_encode_ascii(input, "??", eh) == "<FOO>abc<FOO>"
    assert lst == [("??", "ascii", input, 0, 2),
                   ("??", "ascii", input, 5, 7)]

if HAS_HYPOTHESIS:
    @given(strategies.text())
    def test_utf8_encode_ascii_2(u):
        def eh(errors, encoding, reason, p, start, end):
            return "?" * (end - start), end

        assert utf8_encode_ascii(u.encode("utf8"),
                                "replace", eh) == u.encode("ascii", "replace")

def test_str_decode_ascii():
    assert str_decode_ascii("abc", "??", True, "??") == ("abc", 3, 3)
    def eh(errors, encoding, reason, p, start, end):
        lst.append((errors, encoding, p, start, end))
        return u"\u1234\u5678".encode("utf8"), end
    lst = []
    input = "\xe8"
    exp = u"\u1234\u5678".encode("utf8")
    assert str_decode_ascii(input, "??", True, eh) == (exp, 1, 2)
    assert lst == [("??", "ascii", input, 0, 1)]
    lst = []
    input = "\xe8\xe9abc\xea\xeb"
    assert str_decode_ascii(input, "??", True, eh) == (
        exp + exp + "abc" + exp + exp, 7, 11)
    assert lst == [("??", "ascii", input, 0, 1),
                   ("??", "ascii", input, 1, 2),
                   ("??", "ascii", input, 5, 6),
                   ("??", "ascii", input, 6, 7)]
if HAS_HYPOTHESIS:
    @given(strategies.text())
    def test_unicode_raw_escape(u):
        r = uh.utf8_encode_raw_unicode_escape(u.encode("utf8"), 'strict', None)
        assert r == u.encode("raw-unicode-escape")

    @given(strategies.text())
    def test_unicode_escape(u):
        r = uh.utf8_encode_unicode_escape(u.encode("utf8"), "strict", None)
        assert r == u.encode("unicode-escape")

def test_encode_decimal(space):
    assert uh.unicode_encode_decimal(u' 12, 34 ', None) == ' 12, 34 '
    with pytest.raises(ValueError):
        uh.unicode_encode_decimal(u' 12, \u1234 '.encode('utf8'), None)
    state = space.fromcache(CodecState)
    handler = state.encode_error_handler
    assert uh.unicode_encode_decimal(
        u'u\u1234\u1235v'.encode('utf8'), 'replace', handler) == 'u??v'

    result = uh.unicode_encode_decimal(
        u'12\u1234'.encode('utf8'), 'xmlcharrefreplace', handler)
    assert result == '12&#4660;'

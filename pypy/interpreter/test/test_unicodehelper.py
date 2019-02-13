import py
import pytest
from pypy.conftest import option
try:
    from hypothesis import given, strategies
    HAS_HYPOTHESIS = True
except ImportError:
    HAS_HYPOTHESIS = False
import struct
import sys
from pypy.interpreter.unicodehelper import (
    str_decode_utf8, utf8_encode_utf_32_be, str_decode_utf_32_be)
from pypy.interpreter.unicodehelper import encode_utf8sp, decode_utf8sp
from pypy.interpreter.unicodehelper import utf8_encode_ascii, str_decode_ascii
from pypy.interpreter import unicodehelper as uh
from pypy.module._codecs.interp_codecs import CodecState

class Hit(Exception):
    pass

class FakeSpace:
    def __getattr__(self, name):
        if name in ('w_UnicodeEncodeError', 'w_UnicodeDecodeError'):
            raise Hit
        raise AttributeError(name)

def fake_eh(errors, encoding, msg, u, startingpos, endingpos):
    raise Hit()

def decode_utf8(u):
    return str_decode_utf8(u, "strict", True, fake_eh)

def test_decode_utf8():
    assert decode_utf8("abc") == ("abc", 3, 3)
    assert decode_utf8("\xe1\x88\xb4") == ("\xe1\x88\xb4", 1, 3)
    py.test.raises(Hit, decode_utf8, "\xed\xa0\x80")
    py.test.raises(Hit, decode_utf8, "\xed\xb0\x80")
    py.test.raises(Hit, decode_utf8, "\xed\xa0\x80\xed\xb0\x80")
    got = decode_utf8("\xf0\x90\x80\x80")
    assert got == ("\xf0\x90\x80\x80", 1, 4)

def test_utf8_encode_ascii():
    assert utf8_encode_ascii("abc", "??", "??") == "abc"
    def eh(errors, encoding, reason, p, start, end):
        lst.append((errors, encoding, p, start, end))
        return "<FOO>", end, 'b'
    lst = []
    input = u"\u1234".encode("utf8")
    assert utf8_encode_ascii(input, "??", eh) == "<FOO>"
    assert lst == [("??", "ascii", input, 0, 1)]
    lst = []
    input = u"\u1234\u5678abc\u8765\u4321".encode("utf8")
    assert utf8_encode_ascii(input, "??", eh) == "<FOO>abc<FOO>"
    assert lst == [("??", "ascii", input, 0, 2),
                   ("??", "ascii", input, 5, 7)]

@pytest.mark.skip("rework this test for utf8")
def test_decode_utf8_allow_surrogates():
    sp = FakeSpace()
    assert decode_utf8(sp, "\xed\xa0\x80", allow_surrogates=True) == u"\ud800"
    assert decode_utf8(sp, "\xed\xb0\x80", allow_surrogates=True) == u"\udc00"
    got = decode_utf8(sp, "\xed\xa0\x80\xed\xb0\x80", allow_surrogates=True)
    assert map(ord, got) == [0xd800, 0xdc00]
    got = decode_utf8(sp, "\xf0\x90\x80\x80", allow_surrogates=True)
    assert map(ord, got) == [0x10000]

@pytest.mark.skip("rework this test for utf8")
def test_decode_utf8sp():
    space = FakeSpace()
    assert decode_utf8sp(space, "\xed\xa0\x80") == u"\ud800"
    assert decode_utf8sp(space, "\xed\xb0\x80") == u"\udc00"
    got = decode_utf8sp(space, "\xed\xa0\x80\xed\xb0\x80")
    assert map(ord, got) == [0xd800, 0xdc00]
    got = decode_utf8sp(space, "\xf0\x90\x80\x80")
    assert map(ord, got) == [0x10000]

@pytest.mark.skip("test has non-valid errorhandler")
@pytest.mark.parametrize('unich', [u"\ud800", u"\udc80"])
def test_utf32_surrogates(unich):
    assert (utf8_encode_utf_32_be(unich.encode('utf-8'), None) ==
            struct.pack('>i', ord(unich)))
    with pytest.raises(UnicodeEncodeError):
        def errorhandler(errors, enc, msg, b, startingpos, endingpos):
             u = b.decode('utf-8')
             raise UnicodeEncodeError(enc, u, startingpos, endingpos, msg)
        utf8_encode_utf_32_be(unich.encode('utf-8'), None, errorhandler,
                              allow_surrogates=False)

    def replace_with(ru, rs):
        if rs:
            rs = rs.encode('utf-8')
        def errorhandler(errors, enc, msg, u, startingpos, endingpos):
            if errors == 'strict':
                raise UnicodeEncodeError(enc, u, startingpos, endingpos, msg)
            return rs, endingpos
        uch = u"<%s>" % unich
        return utf8_encode_utf_32_be(
            uch.encode('utf8'), None,
            errorhandler, allow_surrogates=False)
    assert replace_with(u'rep', None) == u'<rep>'.encode('utf-32-be')
    assert (replace_with(None, '\xca\xfe\xca\xfe') ==
            '\x00\x00\x00<\xca\xfe\xca\xfe\x00\x00\x00>')

    with pytest.raises(UnicodeDecodeError):
        str_decode_utf_32_be(b"\x00\x00\xdc\x80", 4, None)

def test_str_decode_ascii():
    assert str_decode_ascii("abc", "??", True, "??") == ("abc", 3, 3)
    def eh(errors, encoding, reason, p, start, end):
        lst.append((errors, encoding, p, start, end))
        return u"\u1234\u5678".encode("utf8"), end, 'u'
    lst = []
    input = "\xe8"
    exp = u"\u1234\u5678".encode("utf8")
    assert str_decode_ascii(input, "??", True, eh) == (exp, 2, 2)
    assert lst == [("??", "ascii", input, 0, 1)]
    lst = []
    input = "\xe8\xe9abc\xea\xeb"
    assert str_decode_ascii(input, "??", True, eh) == (
        exp + exp + "abc" + exp + exp, 11, 11)
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

    @given(strategies.text())
    def test_utf8_encode_ascii_2(u):
        def eh(errors, encoding, reason, p, start, end):
            return "?" * (end - start), end, 'b'
        assert utf8_encode_ascii(u.encode("utf8"), "replace", eh) == u.encode("ascii", "replace")

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

@pytest.mark.skipif(sys.platform != 'win32', reason='Windows only test')
def test_encode_mbcs(space):
    u = u"abc" + u"-\u5171\u0141\u2661\u0363\uDC80"
    utf8 = u.encode('utf8')
    with pytest.raises(UnicodeEncodeError):
        def eh(errors, enc, msg, b, startingpos, endingpos):
             u = b.decode('utf-8')
             raise UnicodeEncodeError(enc, u, startingpos, endingpos, msg)
        uh.utf8_encode_mbcs(utf8, 'strict', eh)

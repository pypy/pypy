import py
import pytest
import struct
import sys
from pypy.interpreter.unicodehelper import (
    encode_utf8, decode_utf8, unicode_encode_utf_32_be, str_decode_utf_32_be)
from pypy.interpreter.unicodehelper import encode_utf8sp, decode_utf8sp


class Hit(Exception):
    pass

class FakeSpace:
    def __getattr__(self, name):
        if name in ('w_UnicodeEncodeError', 'w_UnicodeDecodeError'):
            raise Hit
        raise AttributeError(name)


def test_encode_utf8():
    space = FakeSpace()
    assert encode_utf8(space, u"abc") == "abc"
    assert encode_utf8(space, u"\u1234") == "\xe1\x88\xb4"
    py.test.raises(Hit, encode_utf8, space, u"\ud800")
    py.test.raises(Hit, encode_utf8, space, u"\udc00")
    # for the following test, go to lengths to avoid CPython's optimizer
    # and .pyc file storage, which collapse the two surrogates into one
    c = u"\udc00"
    py.test.raises(Hit, encode_utf8, space, u"\ud800" + c)

def test_encode_utf8_allow_surrogates():
    sp = FakeSpace()
    assert encode_utf8(sp, u"\ud800", allow_surrogates=True) == "\xed\xa0\x80"
    assert encode_utf8(sp, u"\udc00", allow_surrogates=True) == "\xed\xb0\x80"
    c = u"\udc00"
    got = encode_utf8(sp, u"\ud800" + c, allow_surrogates=True)
    assert got == "\xf0\x90\x80\x80"

def test_encode_utf8sp():
    sp = FakeSpace()
    assert encode_utf8sp(sp, u"\ud800") == "\xed\xa0\x80"
    assert encode_utf8sp(sp, u"\udc00") == "\xed\xb0\x80"
    c = u"\udc00"
    got = encode_utf8sp(sp, u"\ud800" + c)
    assert got == "\xed\xa0\x80\xed\xb0\x80"

def test_decode_utf8():
    space = FakeSpace()
    assert decode_utf8(space, "abc") == u"abc"
    assert decode_utf8(space, "\xe1\x88\xb4") == u"\u1234"
    py.test.raises(Hit, decode_utf8, space, "\xed\xa0\x80")
    py.test.raises(Hit, decode_utf8, space, "\xed\xb0\x80")
    py.test.raises(Hit, decode_utf8, space, "\xed\xa0\x80\xed\xb0\x80")
    got = decode_utf8(space, "\xf0\x90\x80\x80")
    if sys.maxunicode > 65535:
        assert map(ord, got) == [0x10000]
    else:
        assert map(ord, got) == [55296, 56320]

def test_decode_utf8_allow_surrogates():
    sp = FakeSpace()
    assert decode_utf8(sp, "\xed\xa0\x80", allow_surrogates=True) == u"\ud800"
    assert decode_utf8(sp, "\xed\xb0\x80", allow_surrogates=True) == u"\udc00"
    got = decode_utf8(sp, "\xed\xa0\x80\xed\xb0\x80", allow_surrogates=True)
    assert map(ord, got) == [0xd800, 0xdc00]
    got = decode_utf8(sp, "\xf0\x90\x80\x80", allow_surrogates=True)
    assert map(ord, got) == [0x10000]

def test_decode_utf8sp():
    space = FakeSpace()
    assert decode_utf8sp(space, "\xed\xa0\x80") == u"\ud800"
    assert decode_utf8sp(space, "\xed\xb0\x80") == u"\udc00"
    got = decode_utf8sp(space, "\xed\xa0\x80\xed\xb0\x80")
    assert map(ord, got) == [0xd800, 0xdc00]
    got = decode_utf8sp(space, "\xf0\x90\x80\x80")
    assert map(ord, got) == [0x10000]

@pytest.mark.parametrize('unich', [u"\ud800", u"\udc80"])
def test_utf32_surrogates(unich):
    assert (unicode_encode_utf_32_be(unich, 1, None) ==
            struct.pack('>i', ord(unich)))
    with pytest.raises(UnicodeEncodeError):
        unicode_encode_utf_32_be(unich, 1, None, allow_surrogates=False)

    def replace_with(ru, rs):
        def errorhandler(errors, enc, msg, u, startingpos, endingpos):
            if errors == 'strict':
                raise UnicodeEncodeError(enc, u, startingpos, endingpos, msg)
            return ru, rs, endingpos
        return unicode_encode_utf_32_be(
            u"<%s>" % unich, 3, None,
            errorhandler, allow_surrogates=False)

    assert replace_with(u'rep', None) == u'<rep>'.encode('utf-32-be')
    assert (replace_with(None, '\xca\xfe\xca\xfe') ==
            '\x00\x00\x00<\xca\xfe\xca\xfe\x00\x00\x00>')

    with pytest.raises(UnicodeDecodeError):
        str_decode_utf_32_be(b"\x00\x00\xdc\x80", 4, None)

import pytest
import struct
import sys
from pypy.interpreter.unicodehelper import (
    encode_utf8, decode_utf8, unicode_encode_utf_32_be)

class FakeSpace:
    pass

def test_encode_utf8():
    space = FakeSpace()
    assert encode_utf8(space, u"abc") == "abc"
    assert encode_utf8(space, u"\u1234") == "\xe1\x88\xb4"
    assert encode_utf8(space, u"\ud800") == "\xed\xa0\x80"
    assert encode_utf8(space, u"\udc00") == "\xed\xb0\x80"
    # for the following test, go to lengths to avoid CPython's optimizer
    # and .pyc file storage, which collapse the two surrogates into one
    c = u"\udc00"
    assert encode_utf8(space, u"\ud800" + c) == "\xf0\x90\x80\x80"

def test_decode_utf8():
    space = FakeSpace()
    assert decode_utf8(space, "abc") == u"abc"
    assert decode_utf8(space, "\xe1\x88\xb4") == u"\u1234"
    assert decode_utf8(space, "\xed\xa0\x80") == u"\ud800"
    assert decode_utf8(space, "\xed\xb0\x80") == u"\udc00"
    got = decode_utf8(space, "\xed\xa0\x80\xed\xb0\x80")
    assert map(ord, got) == [0xd800, 0xdc00]
    got = decode_utf8(space, "\xf0\x90\x80\x80")
    if sys.maxunicode > 65535:
        assert map(ord, got) == [0x10000]
    else:
        assert map(ord, got) == [55296, 56320]

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

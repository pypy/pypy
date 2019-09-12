import pytest

from pypy.interpreter.unicodehelper import (
    utf8_encode_utf_8, decode_utf8sp, ErrorHandlerError
)


class Hit(Exception):
    pass

class FakeSpace:
    def __getattr__(self, name):
        if name in ('w_UnicodeEncodeError', 'w_UnicodeDecodeError'):
            raise Hit
        raise AttributeError(name)


def test_encode_utf_8_combine_surrogates():
    """
    In the case of a surrogate pair, the error handler should
    called with a start and stop position of the full surrogate
    pair (new behavior in python3.6)
    """
    #               /--surrogate pair--\
    #    \udc80      \ud800      \udfff
    b = "\xed\xb2\x80\xed\xa0\x80\xed\xbf\xbf"

    calls = []

    def errorhandler(errors, encoding, msg, s, start, end):
        """
        This handler will be called twice, so asserting both times:

        1. the first time, 0xDC80 will be handled as a single surrogate,
           since it is a standalone character and an invalid surrogate.
        2. the second time, the characters will be 0xD800 and 0xDFFF, since
           that is a valid surrogate pair.
        """
        calls.append(s.decode("utf-8")[start:end])
        return 'abc', end, 'b'

    res = utf8_encode_utf_8(
        b, 'strict',
        errorhandler=errorhandler,
        allow_surrogates=False
    )
    assert res == "abcabc"
    assert calls == [u'\udc80', u'\uD800\uDFFF']

def test_bad_error_handler():
    b = u"\udc80\ud800\udfff".encode("utf-8")
    def errorhandler(errors, encoding, msg, s, start, end):
        return '', start, 'b' # returned index is too small

    pytest.raises(ErrorHandlerError, utf8_encode_utf_8, b, 'strict',
                  errorhandler=errorhandler, allow_surrogates=False)

def test_decode_utf8sp():
    space = FakeSpace()
    assert decode_utf8sp(space, "\xed\xa0\x80") == ("\xed\xa0\x80", 1, 3)
    assert decode_utf8sp(space, "\xed\xb0\x80") == ("\xed\xb0\x80", 1, 3)
    got = decode_utf8sp(space, "\xed\xa0\x80\xed\xb0\x80")
    assert map(ord, got[0].decode('utf8')) == [0xd800, 0xdc00]
    got = decode_utf8sp(space, "\xf0\x90\x80\x80")
    assert map(ord, got[0].decode('utf8')) == [0x10000]


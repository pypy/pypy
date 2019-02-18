from pypy.interpreter.unicodehelper import (
    utf8_encode_utf_8, decode_utf8sp,
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
    return back a start and stop position of the full surrogate
    pair (new behavior inherited from python3.6)
    """
    u = u"\udc80\ud800\udfff"

    handler_num = 0

    def errorhandler(errors, encoding, msg, s, start, end):
        """
        This handler will be called twice, so asserting both times:

        1. the first time, 0xDC80 will be handled as a single surrogate,
           since it is a standalone character and an invalid surrogate.
        2. the second time, the characters will be 0xD800 and 0xDFFF, since
           that is a valid surrogate pair.
        """
        assert s[start:end] in [u'\udc80', u'\uD800\uDFFF']
        return '', 0, end

    utf8_encode_utf_8(
        u, 'strict',
        errorhandler=errorhandler,
        allow_surrogates=False
    )

def test_decode_utf8sp():
    space = FakeSpace()
    assert decode_utf8sp(space, "\xed\xa0\x80") == ("\xed\xa0\x80", 1, 3)
    assert decode_utf8sp(space, "\xed\xb0\x80") == ("\xed\xb0\x80", 1, 3)
    got = decode_utf8sp(space, "\xed\xa0\x80\xed\xb0\x80")
    assert map(ord, got[0].decode('utf8')) == [0xd800, 0xdc00]
    got = decode_utf8sp(space, "\xf0\x90\x80\x80")
    assert map(ord, got[0].decode('utf8')) == [0x10000]


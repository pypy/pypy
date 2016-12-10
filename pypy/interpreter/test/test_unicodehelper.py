import py
from pypy.interpreter.unicodehelper import encode_utf8, decode_utf8


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

def test_decode_utf8():
    space = FakeSpace()
    assert decode_utf8(space, "abc") == u"abc"
    assert decode_utf8(space, "\xe1\x88\xb4") == u"\u1234"
    py.test.raises(Hit, decode_utf8, space, "\xed\xa0\x80")
    py.test.raises(Hit, decode_utf8, space, "\xed\xb0\x80")
    py.test.raises(Hit, decode_utf8, space, "\xed\xa0\x80\xed\xb0\x80")
    got = decode_utf8(space, "\xf0\x90\x80\x80")
    assert map(ord, got) == [0x10000]

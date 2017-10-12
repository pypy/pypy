import py
from pypy.interpreter.unicodehelper import encode_utf8, decode_utf8
from pypy.interpreter.unicodehelper import utf8_encode_ascii, str_decode_ascii


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
    assert decode_utf8(space, "abc") == ("abc", 3)
    assert decode_utf8(space, "\xe1\x88\xb4") == ("\xe1\x88\xb4", 1)
    assert decode_utf8(space, "\xed\xa0\x80") == ("\xed\xa0\x80", 1)
    assert decode_utf8(space, "\xed\xb0\x80") == ("\xed\xb0\x80", 1)
    assert decode_utf8(space, "\xed\xa0\x80\xed\xb0\x80") == (
        "\xed\xa0\x80\xed\xb0\x80", 2)
    assert decode_utf8(space, "\xf0\x90\x80\x80") == ("\xf0\x90\x80\x80", 1)

def test_utf8_encode_ascii():
    assert utf8_encode_ascii("abc", 3, "??", "??") == "abc"
    py.test.skip("test me more...")

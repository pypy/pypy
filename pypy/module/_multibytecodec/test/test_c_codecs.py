import py
from pypy.module._multibytecodec.c_codecs import getcodec, codecs
from pypy.module._multibytecodec.c_codecs import decode, encode
from pypy.module._multibytecodec.c_codecs import EncodeDecodeError


def test_codecs_existence():
    for name in codecs:
        c = getcodec(name)
        assert c
    py.test.raises(KeyError, getcodec, "foobar")

def test_decode_gbk():
    c = getcodec("gbk")
    u = decode(c, "\xA1\xAA")
    assert u == unichr(0x2014)
    u = decode(c, "foobar")
    assert u == u"foobar"

def test_decode_hz():
    # stateful
    c = getcodec("hz")
    u = decode(c, "~{abc}")
    assert u == u'\u5f95\u6cef'

def test_decode_hz_error():
    # error
    c = getcodec("hz")
    e = py.test.raises(EncodeDecodeError, decode, c, "~{}").value
    assert e.start == 2
    assert e.end == 3
    assert e.reason == "incomplete multibyte sequence"
    #
    e = py.test.raises(EncodeDecodeError, decode, c, "~{xyz}").value
    assert e.start == 2
    assert e.end == 4
    assert e.reason == "illegal multibyte sequence"

def test_encode_hz():
    c = getcodec("hz")
    s = encode(c, u'foobar')
    assert s == 'foobar' and type(s) is str
    s = encode(c, u'\u5f95\u6cef')
    assert s == '~{abc}~}'

def test_encode_hz_error():
    # error
    c = getcodec("hz")
    e = py.test.raises(EncodeDecodeError, encode, c, u'abc\u1234def').value
    assert e.start == 3
    assert e.end == 4
    assert e.reason == "illegal multibyte sequence"

def test_encode_jisx0208():
    c = getcodec('iso2022_jp')
    s = encode(c, u'\u83ca\u5730\u6642\u592b')
    assert s == '\x1b$B5FCO;~IW\x1b(B' and type(s) is str

import py
from pypy.module._multibytecodec.c_codecs import getcodec, codecs
from pypy.module._multibytecodec.c_codecs import decode, EncodeDecodeError


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

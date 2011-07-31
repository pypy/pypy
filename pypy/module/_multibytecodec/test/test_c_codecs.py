import py
from pypy.module._multibytecodec.c_codecs import getcodec, codecs
from pypy.module._multibytecodec.c_codecs import decode, encode
from pypy.module._multibytecodec.c_codecs import EncodeDecodeError
from pypy.module._multibytecodec import c_codecs


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
    u = decode(c, "~{")
    assert u == u''

def test_decodeex_hz():
    c = getcodec("hz")
    decodebuf = c_codecs.pypy_cjk_dec_new(c)
    u = c_codecs.decodeex(decodebuf, "~{abcd~}")
    assert u == u'\u5f95\u6c85'
    u = c_codecs.decodeex(decodebuf, "~{efgh~}")
    assert u == u'\u5f50\u73b7'
    u = c_codecs.decodeex(decodebuf, "!~{abcd~}xyz~{efgh")
    assert u == u'!\u5f95\u6c85xyz\u5f50\u73b7'
    c_codecs.pypy_cjk_dec_free(decodebuf)

def test_decodeex_hz_incomplete():
    c = getcodec("hz")
    decodebuf = c_codecs.pypy_cjk_dec_new(c)
    buf = ''
    for c, output in zip("!~{abcd~}xyz~{efgh",
          [u'!',  # !
           u'',   # ~
           u'',   # {
           u'',   # a
           u'\u5f95',   # b
           u'',   # c
           u'\u6c85',   # d
           u'',   # ~
           u'',   # }
           u'x',  # x
           u'y',  # y
           u'z',  # z
           u'',   # ~
           u'',   # {
           u'',   # e
           u'\u5f50',   # f
           u'',   # g
           u'\u73b7',   # h
           ]):
        buf += c
        incompletepos = [len(buf)]
        u = c_codecs.decodeex(decodebuf, buf, incompletepos=incompletepos)
        assert u == output
        buf = buf[incompletepos[0]:]
    assert buf == ''
    c_codecs.pypy_cjk_dec_free(decodebuf)

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

def test_decode_hz_ignore():
    c = getcodec("hz")
    u = decode(c, 'def~{}abc', 'ignore')
    assert u == u'def\u5fcf'

def test_decode_hz_replace():
    c = getcodec("hz")
    u = decode(c, 'def~{}abc', 'replace')
    assert u == u'def\ufffd\u5fcf'

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

def test_encode_hz_ignore():
    c = getcodec("hz")
    s = encode(c, u'abc\u1234def', 'ignore')
    assert s == 'abcdef'

def test_encode_hz_replace():
    c = getcodec("hz")
    s = encode(c, u'abc\u1234def', 'replace')
    assert s == 'abc?def'

def test_encode_jisx0208():
    c = getcodec('iso2022_jp')
    s = encode(c, u'\u83ca\u5730\u6642\u592b')
    assert s == '\x1b$B5FCO;~IW\x1b(B' and type(s) is str

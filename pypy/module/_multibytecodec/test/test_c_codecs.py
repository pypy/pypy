import py
import pytest
from pypy.module._multibytecodec.c_codecs import getcodec, codecs
from pypy.module._multibytecodec.c_codecs import decode, encode
from pypy.module._multibytecodec.c_codecs import EncodeDecodeError
from pypy.module._multibytecodec import c_codecs


def test_codecs_existence():
    for name in codecs:
        c = getcodec(name)
        assert c
    py.test.raises(KeyError, getcodec, "foobar")

def test_decode_gbk(space):
    c = getcodec("gbk")
    u = decode(space, c, "\xA1\xAA")
    assert u == unichr(0x2014).encode('utf8')
    u = decode(space, c, "foobar")
    assert u == "foobar"

@pytest.mark.parametrize('undecodable', [
    b"abc\x80\x80\xc1\xc4",
    b"\xff\x30\x81\x30", b"\x81\x30\xff\x30",  # bpo-29990
])
def test_decode_gb18030_error(space, undecodable):
    c = getcodec("gb18030")
    with pytest.raises(EncodeDecodeError):
        decode(space, c, undecodable)

def test_decode_hz(space):
    # stateful
    c = getcodec("hz")
    utf8 = decode(space, c, "~{abc}")
    assert utf8.decode('utf8') == u'\u5f95\u6cef'
    u = decode(space, c, "~{")
    assert u == u''

def test_decodeex_hz(space):
    c = getcodec("hz")
    decodebuf = c_codecs.pypy_cjk_dec_new(c)
    u = c_codecs.decodeex(space, decodebuf, "~{abcd~}")
    assert u == u'\u5f95\u6c85'.encode('utf8')
    u = c_codecs.decodeex(space, decodebuf, "~{efgh~}")
    assert u == u'\u5f50\u73b7'.encode('utf8')
    u = c_codecs.decodeex(space, decodebuf, "!~{abcd~}xyz~{efgh")
    assert u == u'!\u5f95\u6c85xyz\u5f50\u73b7'.encode('utf8')
    c_codecs.pypy_cjk_dec_free(decodebuf)

def test_decodeex_hz_incomplete(space):
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
        u = c_codecs.decodeex(space, decodebuf, buf,
                              ignore_error = c_codecs.MBERR_TOOFEW)
        assert u == output.encode('utf8')
        incompletepos = c_codecs.pypy_cjk_dec_inbuf_consumed(decodebuf)
        buf = buf[incompletepos:]
    assert buf == ''
    c_codecs.pypy_cjk_dec_free(decodebuf)

def test_decode_hz_error(space):
    # error
    c = getcodec("hz")
    e = py.test.raises(EncodeDecodeError, decode, space, c, "~{}").value
    assert e.start == 2
    assert e.end == 3
    assert e.reason == "incomplete multibyte sequence"
    #
    e = py.test.raises(EncodeDecodeError, decode, space, c, "~{xyz}").value
    assert e.start == 2
    assert e.end == 3
    assert e.reason == "illegal multibyte sequence"

def test_decode_hz_ignore(space):
    c = getcodec("hz")
    utf8 = decode(space, c, 'def~{}abc', 'ignore')
    assert utf8.decode('utf8') == u'def\u5f95'

def test_decode_hz_replace(space):
    c = getcodec("hz")
    utf8 = decode(space, c, 'def~{}abc', 'replace')
    assert utf8.decode('utf8') == u'def\ufffd\u5f95\ufffd'

def test_encode_hz(space):
    c = getcodec("hz")
    s = encode(space, c, u'foobar'.encode('utf8'), 6)
    assert s == 'foobar' and type(s) is str
    s = encode(space, c, u'\u5f95\u6cef'.encode('utf8'), 2)
    assert s == '~{abc}~}'
    # bpo-30003
    s = encode(space, c, 'ab~cd', 5)
    assert s == 'ab~~cd'

def test_encode_hz_error(space):
    # error
    c = getcodec("hz")
    e = py.test.raises(EncodeDecodeError, encode, space, c, u'abc\u1234def'.encode('utf8'), 7).value
    assert e.start == 3
    assert e.end == 4
    assert e.reason == "illegal multibyte sequence"

def test_encode_hz_ignore(space):
    c = getcodec("hz")
    s = encode(space, c, u'abc\u1234def'.encode('utf8'), 7, 'ignore')
    assert s == 'abcdef'

def test_encode_hz_replace(space):
    c = getcodec("hz")
    s = encode(space, c, u'abc\u1234def'.encode('utf8'), 7, 'replace')
    assert s == 'abc?def'

def test_encode_jisx0208(space):
    c = getcodec('iso2022_jp')
    s = encode(space, c, u'\u83ca\u5730\u6642\u592b'.encode('utf8'), 4)
    assert s == '\x1b$B5FCO;~IW\x1b(B' and type(s) is str

def test_enc_getstate_iso2022_jp(space):
    # iso2022_jp initial codec state has ASCII mode flags \x42\x42
    c = getcodec('iso2022_jp')
    encodebuf = c_codecs.pypy_cjk_enc_new(c)
    state = c_codecs.enc_getstate(encodebuf)
    assert state == '\x42\x42\x00\x00\x00\x00\x00\x00'
    c_codecs.pypy_cjk_enc_free(encodebuf)

def test_enc_setstate_restores_mode(space):
    c = getcodec('iso2022_jp')
    encodebuf = c_codecs.pypy_cjk_enc_new(c)
    # use MBERR_TOOFEW to avoid resetting state (incremental encode style)
    c_codecs.encodeex(space, encodebuf, u'\u3042'.encode('utf-8'), 1,
                      ignore_error=c_codecs.MBERR_TOOFEW)
    jp_state = c_codecs.enc_getstate(encodebuf)
    assert jp_state != '\x42\x42\x00\x00\x00\x00\x00\x00'
    # restore ASCII state, confirm JIS mode is gone
    ascii_state = '\x42\x42\x00\x00\x00\x00\x00\x00'
    c_codecs.enc_setstate(encodebuf, ascii_state)
    assert c_codecs.enc_getstate(encodebuf) == ascii_state
    # restore JIS state; encoding \u3042 should not emit mode-switch prefix
    c_codecs.enc_setstate(encodebuf, jp_state)
    out = c_codecs.encodeex(space, encodebuf, u'\u3042'.encode('utf-8'), 1,
                            ignore_error=c_codecs.MBERR_TOOFEW)
    assert out == '\x24\x22'
    c_codecs.pypy_cjk_enc_free(encodebuf)

def test_encode_custom_error_handler_bytes(space):
    py.test.skip("needs revamping in py3k")
    c = getcodec("hz")
    def errorhandler(errors, enc, msg, w_t, startingpos, endingpos):
        return u'\xc3'.encode('utf8'), endingpos
    s = encode(space, c, u'abc\u1234def'.encode('utf8'), 7, 'foo', errorhandler)
    assert '\xc3' in s

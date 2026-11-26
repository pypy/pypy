# spaceconfig = {"usemodules": ["_multibytecodec"]}
import pytest
import codecs
import sys

import _codecs_cn


def test_missing_codec():
    pytest.raises(LookupError, _codecs_cn.getcodec, "foobar")

def test_decode_hz():
    codec = _codecs_cn.getcodec("hz")
    r = codec.decode("~{abc}")
    assert r == (u'\u5f95\u6cef', 6)

def test_strict_error():
    codec = _codecs_cn.getcodec("hz")
    r = codec.decode("~{abc}", "strict")
    assert r == (u'\u5f95\u6cef', 6)
    assert type(r[0]) is unicode

def test_decode_hz_error():
    codec = _codecs_cn.getcodec("hz")
    with pytest.raises(UnicodeDecodeError) as exc_info:
        codec.decode("~{}")
    e = exc_info.value
    assert e.args == ('hz', '~{}', 2, 3, 'incomplete multibyte sequence')
    assert e.encoding == 'hz'
    assert e.object == '~{}' and type(e.object) is str
    assert e.start == 2
    assert e.end == 3
    assert e.reason == "incomplete multibyte sequence"
    #
    with pytest.raises(UnicodeDecodeError) as exc_info:
        codec.decode("~{xyz}")
    e = exc_info.value
    assert e.args == ('hz', '~{xyz}', 2, 3, 'illegal multibyte sequence')

def test_decode_hz_tilde():
    # bpo-30003
    assert "ab~~cd".decode("hz") == u"ab~cd"
    assert u"ab~cd".encode("hz") == "ab~~cd"

def test_jisx0213_pair_lookahead():
    # a kana that can start a JIS X 0213 pair, followed by one
    # that does not complete it, must not swallow the second one
    s = u'\u304b\u3057'
    for codec in ("iso-2022-jp-3", "iso-2022-jp-2004",
                  "euc-jis-2004", "shift-jis-2004"):
        assert s.encode(codec).decode(codec) == s
    assert u'\u304b\u309a'.encode("iso-2022-jp-3") == '\x1b$(O$w\x1b(B'

def test_decode_hz_ignore():
    codec = _codecs_cn.getcodec("hz")
    r = codec.decode("def~{}abc", errors='ignore')
    assert r == (u'def\u5f95', 9)
    r = codec.decode("def~{}abc", 'ignore')
    assert r == (u'def\u5f95', 9)

def test_decode_hz_replace():
    codec = _codecs_cn.getcodec("hz")
    r = codec.decode("def~{}abc", errors='replace')
    assert r == (u'def\ufffd\u5f95\ufffd', 9)
    r = codec.decode("def~{}abc", 'replace')
    assert r == (u'def\ufffd\u5f95\ufffd', 9)

def test_decode_custom_error_handler():
    codecs.register_error("test.decode_custom_error_handler",
                          lambda e: (u'\u1234\u5678', e.end))
    u = "abc\xDD".decode("hz", "test.decode_custom_error_handler")
    assert u == u'abc\u1234\u5678'

def test_decode_custom_error_handler_overflow():
    codecs.register_error("test.test_decode_custom_error_handler_overflow",
                          lambda e: (u'', sys.maxint + 1))
    pytest.raises((IndexError, OverflowError), "abc\xDD".decode, "hz",
                  "test.test_decode_custom_error_handler_overflow")

def test_encode_hz():
    codec = _codecs_cn.getcodec("hz")
    r = codec.encode(u'\u5f95\u6cef')
    assert r == ('~{abc}~}', 2)
    assert type(r[0]) is str

def test_encode_hz_error():
    codec = _codecs_cn.getcodec("hz")
    u = u'abc\u1234def'
    with pytest.raises(UnicodeEncodeError) as exc_info:
        codec.encode(u)
    e = exc_info.value
    assert e.args == ('hz', u, 3, 4, 'illegal multibyte sequence')
    assert e.encoding == 'hz'
    assert e.object == u and type(e.object) is unicode
    assert e.start == 3
    assert e.end == 4
    assert e.reason == 'illegal multibyte sequence'

def test_encode_hz_ignore():
    codec = _codecs_cn.getcodec("hz")
    r = codec.encode(u'abc\u1234def', 'ignore')
    assert r == ('abcdef', 7)
    assert type(r[0]) is str

def test_encode_hz_replace():
    codec = _codecs_cn.getcodec("hz")
    r = codec.encode(u'abc\u1234def', 'replace')
    assert r == ('abc?def', 7)
    assert type(r[0]) is str

def test_encode_custom_error_handler():
    codecs.register_error("test.multi_bad_handler", lambda e: (repl, 1))
    repl = u"\u2014"
    s = u"\uDDA1".encode("gbk", "test.multi_bad_handler")
    assert s == '\xA1\xAA'

def test_encode_custom_error_handler_type():
    codecs.register_error("test.test_encode_custom_error_handler_type",
                          lambda e: ('\xc3', e.end))
    raises(TypeError, u"\uDDA1".encode, "gbk",
           "test.test_encode_custom_error_handler_type")

def test_encode_replacement_with_state():
    s = u'\u4ee4\u477c\u4ee4'.encode("iso-2022-jp", errors="replace")
    assert s == '\x1b$BNa\x1b(B?\x1b$BNa\x1b(B'

def test_streaming_codec():
    test_0 = u'\uc5fc\u76d0\u5869\u9e7d\u477c\u4e3d/\u3012'
    test_1 = u'\u4ee4\u477c\u3080\u304b\u3057\u3080\u304b\u3057\u3042\u308b\u3068\u3053\u308d\u306b'
    test_2 = u' foo = "Quoted string ****\u4ee4\u477c" '

    ereplace = {'errors': 'replace'}
    exml = {'errors': 'xmlcharrefreplace'}
    for codec in ("iso-2022-jp", "iso-2022-jp-ext", "iso-2022-jp-1",
                  "iso-2022-jp-2", "iso-2022-jp-3", "iso-2022-jp-2004",
                  "iso-2022-kr",
                 ):

        out_1 = test_1.encode(codec, **ereplace).decode(codec, **ereplace)
        assert out_1.endswith(u'\u3080\u304b\u3057\u3080\u304b\u3057\u3042\u308b\u3068\u3053\u308d\u306b')

        out_0a = test_0.encode(codec, **ereplace).decode(codec, **ereplace)
        for n, char in enumerate(out_0a):
            assert char in (test_0[n], "?")

        out_0b = test_0.encode(codec, **exml).decode(codec, **ereplace)
        assert "&#18300;" in out_0b

        out_2 = test_2.encode(codec, **ereplace).decode(codec, **ereplace)
        assert out_2.count('"') == 2

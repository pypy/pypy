import pytest
import codecs
import sys

import _codecs_cn


def test_missing_codec():
    pytest.raises(LookupError, _codecs_cn.getcodec, "foobar")


def test_decode_hz():
    codec = _codecs_cn.getcodec("hz")
    r = codec.decode(b"~{abc}")
    assert r == ('\u5f95\u6cef', 6)


def test_strict_error():
    codec = _codecs_cn.getcodec("hz")
    r = codec.decode(b"~{abc}", "strict")
    assert r == ('\u5f95\u6cef', 6)
    assert type(r[0]) is str


def test_decode_hz_error():
    codec = _codecs_cn.getcodec("hz")
    with pytest.raises(UnicodeDecodeError) as exc_info:
        codec.decode(b"~{}")
    e = exc_info.value
    assert e.args == ('hz', b'~{}', 2, 3, 'incomplete multibyte sequence')
    assert e.encoding == 'hz'
    assert e.object == b'~{}' and type(e.object) is bytes
    assert e.start == 2
    assert e.end == 3
    assert e.reason == "incomplete multibyte sequence"
    #
    with pytest.raises(UnicodeDecodeError) as exc_info:
        codec.decode(b"~{xyz}")
    e = exc_info.value
    assert e.args == ('hz', b'~{xyz}', 2, 3, 'illegal multibyte sequence')


def test_decode_hz_ignore():
    codec = _codecs_cn.getcodec("hz")
    r = codec.decode(b"def~{}abc", errors='ignore')
    assert r == ('def\u5f95', 9)
    r = codec.decode(b"def~{}abc", 'ignore')
    assert r == ('def\u5f95', 9)


def test_decode_hz_replace():
    codec = _codecs_cn.getcodec("hz")
    r = codec.decode(b"def~{}abc", errors='replace')
    assert r == ('def\ufffd\u5f95\ufffd', 9)
    r = codec.decode(b"def~{}abc", 'replace')
    assert r == ('def\ufffd\u5f95\ufffd', 9)


def test_decode_custom_error_handler():
    codecs.register_error("test.decode_custom_error_handler",
                          lambda e: ('\u1234\u5678', e.end))
    u = b"abc\xDD".decode("hz", "test.decode_custom_error_handler")
    assert u == 'abc\u1234\u5678'


def test_decode_custom_error_handler_overflow():
    codecs.register_error("test.test_decode_custom_error_handler_overflow",
                          lambda e: ('', sys.maxsize + 1))
    pytest.raises((IndexError, OverflowError), b"abc\xDD".decode, "hz",
                  "test.test_decode_custom_error_handler_overflow")


def test_decode_custom_error_handler_type():
    codecs.register_error("test.test_decode_custom_error_handler_type",
                          lambda e: (b'', e.end))
    pytest.raises(TypeError, b"abc\xDD".decode, "hz",
                  "test.test_decode_custom_error_handler_type")


def test_decode_custom_error_handler_longindex():
    codecs.register_error("test.test_decode_custom_error_handler_longindex",
                          lambda e: ('', sys.maxsize + 1))
    pytest.raises(IndexError, b"abc\xDD".decode, "hz",
                  "test.test_decode_custom_error_handler_longindex")


def test_encode_hz():
    codec = _codecs_cn.getcodec("hz")
    r = codec.encode('\u5f95\u6cef')
    assert r == (b'~{abc}~}', 2)
    assert type(r[0]) is bytes


def test_encode_hz_error():
    codec = _codecs_cn.getcodec("hz")
    u = 'abc\u1234def'
    with pytest.raises(UnicodeEncodeError) as exc_info:
        codec.encode(u)
    e = exc_info.value
    assert e.args == ('hz', u, 3, 4, 'illegal multibyte sequence')
    assert e.encoding == 'hz'
    assert e.object == u and type(e.object) is str
    assert e.start == 3
    assert e.end == 4
    assert e.reason == 'illegal multibyte sequence'


def test_encode_hz_ignore():
    codec = _codecs_cn.getcodec("hz")
    r = codec.encode('abc\u1234def', 'ignore')
    assert r == (b'abcdef', 7)
    assert type(r[0]) is bytes


def test_encode_hz_replace():
    codec = _codecs_cn.getcodec("hz")
    r = codec.encode('abc\u1234def', 'replace')
    assert r == (b'abc?def', 7)
    assert type(r[0]) is bytes


def test_encode_custom_error_handler():
    codecs.register_error("test.multi_bad_handler", lambda e: (repl, 1))
    repl = "\u2014"
    s = "\uDDA1".encode("gbk", "test.multi_bad_handler")
    assert s == b'\xA1\xAA'


def test_encode_custom_error_handler_type():
    codecs.register_error("test.test_encode_custom_error_handler_type",
                          lambda e: (b'\xc3', e.end))
    result = "\uDDA1".encode("gbk", "test.test_encode_custom_error_handler_type")
    assert b'\xc3' in result


def test_encode_replacement_with_state():
    s = '\u4ee4\u477c\u4ee4'.encode("iso-2022-jp", errors="replace")
    assert s == b'\x1b$BNa\x1b(B?\x1b$BNa\x1b(B'


def test_streaming_codec():
    test_0 = '\uc5fc\u76d0\u5869\u9e7d\u477c\u4e3d/\u3012'
    test_1 = '\u4ee4\u477c\u3080\u304b\u3057\u3080\u304b\u3057\u3042\u308b\u3068\u3053\u308d\u306b'
    test_2 = ' foo = "Quoted string ****\u4ee4\u477c" '

    ereplace = {'errors': 'replace'}
    exml = {'errors': 'xmlcharrefreplace'}
    for codec_name in ("iso-2022-jp", "iso-2022-jp-ext", "iso-2022-jp-1",
                       "iso-2022-jp-2", "iso-2022-jp-3", "iso-2022-jp-2004",
                       "iso-2022-kr"):
        out_1 = test_1.encode(codec_name, **ereplace).decode(codec_name, **ereplace)
        assert out_1.endswith('\u3080\u304b\u3057\u3080\u304b\u3057\u3042\u308b\u3068\u3053\u308d\u306b')

        out_0a = test_0.encode(codec_name, **ereplace).decode(codec_name, **ereplace)
        for n, char in enumerate(out_0a):
            assert char in (test_0[n], "?")

        out_0b = test_0.encode(codec_name, **exml).decode(codec_name, **ereplace)
        assert "&#18300;" in out_0b

        out_2 = test_2.encode(codec_name, **ereplace).decode(codec_name, **ereplace)
        assert out_2.count('"') == 2


def test_cpython_gh_101180():
    cc = codecs.lookup('iso2022_jp_2004')
    s = '\u304b\u309a'
    b = cc.encode(s, 'strict')
    assert b == (b'\x1b$(Q$w\x1b(B', 2)

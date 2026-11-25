# spaceconfig = {"usemodules": ["_multibytecodec"]}
import pytest
import _codecs_cn
from _multibytecodec import MultibyteIncrementalDecoder, MultibyteIncrementalEncoder


class IncrementalHzDecoder(MultibyteIncrementalDecoder):
    codec = _codecs_cn.getcodec('hz')


class IncrementalHzEncoder(MultibyteIncrementalEncoder):
    codec = _codecs_cn.getcodec('hz')


class IncrementalBig5hkscsEncoder(MultibyteIncrementalEncoder):
    codec = _codecs_cn.getcodec('big5hkscs')


def test_decode_hz():
    d = IncrementalHzDecoder()
    r = d.decode("~{abcd~}")
    assert r == u'\u5f95\u6c85'
    r = d.decode("~{efgh~}")
    assert r == u'\u5f50\u73b7'
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
        r = d.decode(c)
        assert r == output

def test_decode_hz_final():
    d = IncrementalHzDecoder()
    r = d.decode("~{", True)
    assert r == u''
    pytest.raises(UnicodeDecodeError, d.decode, "~", True)
    pytest.raises(UnicodeDecodeError, d.decode, "~{a", True)

def test_decode_hz_reset():
    d = IncrementalHzDecoder()
    r = d.decode("ab")
    assert r == u'ab'
    r = d.decode("~{")
    assert r == u''
    r = d.decode("ab")
    assert r == u'\u5f95'
    r = d.decode("ab")
    assert r == u'\u5f95'
    d.reset()
    r = d.decode("ab")
    assert r == u'ab'

def test_decode_hz_error():
    d = IncrementalHzDecoder()
    pytest.raises(UnicodeDecodeError, d.decode, "~{abc", True)
    d = IncrementalHzDecoder("ignore")
    r = d.decode("~{abc", True)
    assert r == u'\u5f95'
    d = IncrementalHzDecoder()
    d.errors = "replace"
    r = d.decode("~{abc", True)
    assert r == u'\u5f95\ufffd'

def test_decode_hz_buffer_grow():
    d = IncrementalHzDecoder()
    for i in range(13):
        r = d.decode("a" * (2**i))
        assert r == u"a" * (2**i)

def test_encode_hz():
    e = IncrementalHzEncoder()
    r = e.encode("abcd")
    assert r == 'abcd'
    r = e.encode(u"\u5f95\u6c85")
    assert r == '~{abcd'
    r = e.encode(u"\u5f50")
    assert r == 'ef'
    r = e.encode(u"\u73b7", final=True)
    assert r == 'gh~}'

def test_encode_hz_final():
    e = IncrementalHzEncoder()
    r = e.encode(u"xyz\u5f95\u6c85", True)
    assert r == 'xyz~{abcd~}'
    # This is a bit hard to test, because the only way I can see that
    # encoders can return MBERR_TOOFEW is with surrogates, which only
    # occur with 2-byte unicode characters...  We will just have to
    # trust that the logic works, because it is exactly the same one
    # as in the decode case :-/

def test_encode_hz_reset():
    # Same issue as with test_encode_hz_final
    e = IncrementalHzEncoder()
    r = e.encode(u"xyz\u5f95\u6c85", True)
    assert r == 'xyz~{abcd~}'
    e.reset()
    r = e.encode(u"xyz\u5f95\u6c85")
    assert r == 'xyz~{abcd'
    r = e.encode(u'', final=True)
    assert r == '~}'

def test_encode_hz_noreset():
    text = (u'\u5df1\u6240\u4e0d\u6b32\uff0c\u52ff\u65bd\u65bc\u4eba\u3002'
            u'Bye.')
    out = ''
    e = IncrementalHzEncoder()
    for c in text:
        out += e.encode(c)
    assert out == b'~{<:Ky2;S{#,NpJ)l6HK!#~}Bye.'

def test_encode_hz_error():
    e = IncrementalHzEncoder()
    pytest.raises(UnicodeEncodeError, e.encode, u"\u4321", True)
    e = IncrementalHzEncoder("ignore")
    r = e.encode(u"xy\u4321z", True)
    assert r == 'xyz'
    e = IncrementalHzEncoder()
    e.errors = "replace"
    r = e.encode(u"xy\u4321z", True)
    assert r == 'xy?z'

def test_encode_hz_buffer_grow():
    e = IncrementalHzEncoder()
    for i in range(13):
        r = e.encode(u"a" * (2**i))
        assert r == "a" * (2**i)

def test_encode_big5hkscs():
    #e = IncrementalBig5hkscsEncoder()
    #r = e.encode(u'\xca', True)
    #assert r == '\x88f'
    #r = e.encode(u'\xca', True)
    #assert r == '\x88f'
    #raises(UnicodeEncodeError, e.encode, u'\u0304', True)
    #
    e = IncrementalBig5hkscsEncoder()
    r = e.encode(u'\xca')
    assert r == ''
    r = e.encode(u'\xca')
    assert r == '\x88f'
    r = e.encode(u'\u0304')
    assert r == '\x88b'

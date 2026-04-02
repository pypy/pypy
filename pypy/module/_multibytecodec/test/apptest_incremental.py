import os
import codecs
import pytest

import _codecs_cn
import _codecs_hk
import _codecs_jp
from _multibytecodec import MultibyteIncrementalDecoder, MultibyteIncrementalEncoder

myfile = os.path.dirname(os.path.abspath(__file__))


class IncrementalHzDecoder(MultibyteIncrementalDecoder):
    codec = _codecs_cn.getcodec('hz')


class IncrementalHzEncoder(MultibyteIncrementalEncoder):
    codec = _codecs_cn.getcodec('hz')


class IncrementalBig5hkscsEncoder(MultibyteIncrementalEncoder):
    codec = _codecs_hk.getcodec('big5hkscs')


def test_decode_hz():
    d = IncrementalHzDecoder()
    r = d.decode(b"~{abcd~}")
    assert r == '\u5f95\u6c85'
    r = d.decode(b"~{efgh~}")
    assert r == '\u5f50\u73b7'
    for c, output in zip(b"!~{abcd~}xyz~{efgh",
          ['!',        # !
           '',         # ~
           '',         # {
           '',         # a
           '\u5f95',   # b
           '',         # c
           '\u6c85',   # d
           '',         # ~
           '',         # }
           'x',        # x
           'y',        # y
           'z',        # z
           '',         # ~
           '',         # {
           '',         # e
           '\u5f50',   # f
           '',         # g
           '\u73b7',   # h
           ]):
        r = d.decode(bytes([c]))
        assert r == output


def test_decode_hz_final():
    d = IncrementalHzDecoder()
    r = d.decode(b"~{", True)
    assert r == ''
    pytest.raises(UnicodeDecodeError, d.decode, b"~", True)
    pytest.raises(UnicodeDecodeError, d.decode, b"~{a", True)


def test_decode_hz_reset():
    d = IncrementalHzDecoder()
    r = d.decode(b"ab")
    assert r == 'ab'
    r = d.decode(b"~{")
    assert r == ''
    r = d.decode(b"ab")
    assert r == '\u5f95'
    r = d.decode(b"ab")
    assert r == '\u5f95'
    d.reset()
    r = d.decode(b"ab")
    assert r == 'ab'


def test_decode_hz_error():
    d = IncrementalHzDecoder()
    pytest.raises(UnicodeDecodeError, d.decode, b"~{abc", True)
    d = IncrementalHzDecoder("ignore")
    r = d.decode(b"~{abc", True)
    assert r == '\u5f95'
    d = IncrementalHzDecoder()
    d.errors = "replace"
    r = d.decode(b"~{abc", True)
    assert r == '\u5f95\ufffd'


def test_decode_hz_buffer_grow():
    d = IncrementalHzDecoder()
    for i in range(13):
        r = d.decode(b"a" * (2**i))
        assert r == "a" * (2**i)


def test_encode_hz():
    e = IncrementalHzEncoder()
    r = e.encode("abcd")
    assert r == b'abcd'
    r = e.encode("\u5f95\u6c85")
    assert r == b'~{abcd'
    r = e.encode("\u5f50")
    assert r == b'ef'
    r = e.encode("\u73b7", final=True)
    assert r == b'gh~}'


def test_encode_hz_final():
    e = IncrementalHzEncoder()
    r = e.encode("xyz\u5f95\u6c85", True)
    assert r == b'xyz~{abcd~}'


def test_encode_hz_reset():
    e = IncrementalHzEncoder()
    r = e.encode("xyz\u5f95\u6c85", True)
    assert r == b'xyz~{abcd~}'
    e.reset()
    r = e.encode("xyz\u5f95\u6c85")
    assert r == b'xyz~{abcd'
    r = e.encode('', final=True)
    assert r == b'~}'


def test_encode_hz_noreset():
    text = ('\u5df1\u6240\u4e0d\u6b32\uff0c\u52ff\u65bd\u65bc\u4eba\u3002'
            'Bye.')
    out = b''
    e = IncrementalHzEncoder()
    for c in text:
        out += e.encode(c)
    assert out == b'~{<:Ky2;S{#,NpJ)l6HK!#~}Bye.'


def test_encode_hz_error():
    e = IncrementalHzEncoder()
    pytest.raises(UnicodeEncodeError, e.encode, "\u4321", True)
    e = IncrementalHzEncoder("ignore")
    r = e.encode("xy\u4321z", True)
    assert r == b'xyz'
    e = IncrementalHzEncoder()
    e.errors = "replace"
    r = e.encode("xy\u4321z", True)
    assert r == b'xy?z'


def test_encode_hz_buffer_grow():
    e = IncrementalHzEncoder()
    for i in range(13):
        r = e.encode("a" * (2**i))
        assert r == b"a" * (2**i)


def test_encode_big5hkscs():
    e = IncrementalBig5hkscsEncoder()
    r = e.encode('\xca')
    assert r == b''
    r = e.encode('\xca')
    assert r == b'\x88f'
    r = e.encode('\u0304')
    assert r == b'\x88b'


def test_encoder_state_with_buffer(monkeypatch):
    # euc_jis_2004 stores state as a buffer of pending Unicode chars
    encoder = codecs.getincrementalencoder('euc_jis_2004')()

    initial_state = encoder.getstate()
    assert encoder.encode('\u00e6\u0300') == b'\xab\xc4'
    encoder.setstate(initial_state)
    assert encoder.encode('\u00e6\u0300') == b'\xab\xc4'

    assert encoder.encode('\u00e6') == b''
    partial_state = encoder.getstate()
    assert encoder.encode('\u0300') == b'\xab\xc4'
    encoder.setstate(partial_state)
    assert encoder.encode('\u0300') == b'\xab\xc4'


def test_encoder_state_without_buffer():
    # iso2022_jp stores mode in codec state, not a pending buffer
    encoder = codecs.getincrementalencoder('iso2022_jp')()

    assert encoder.encode('z') == b'z'
    en_state = encoder.getstate()

    assert encoder.encode('\u3042') == b'\x1b\x24\x42\x24\x22'
    jp_state = encoder.getstate()
    assert encoder.encode('z') == b'\x1b\x28\x42z'

    encoder.setstate(jp_state)
    assert encoder.encode('\u3042') == b'\x24\x22'

    encoder.setstate(en_state)
    assert encoder.encode('z') == b'z'


def test_encoder_getstate_expected_values():
    # euc_jis_2004: buffer state
    enc = codecs.getincrementalencoder('euc_jis_2004')()
    assert enc.getstate() == 0
    enc.encode('\u00e6')
    assert enc.getstate() == int.from_bytes(
        b"\x02" b"\xc3\xa6" b"\x00\x00\x00\x00\x00\x00\x00\x00", 'little')
    enc.encode('\u0300')
    assert enc.getstate() == 0

    # iso2022_jp: codec state only
    enc = codecs.getincrementalencoder('iso2022_jp')()
    assert enc.getstate() == int.from_bytes(
        b"\x00" b"\x42\x42\x00\x00\x00\x00\x00\x00", 'little')
    enc.encode('\u3042')
    assert enc.getstate() == int.from_bytes(
        b"\x00" b"\xc2\x42\x00\x00\x00\x00\x00\x00", 'little')


def test_encoder_setstate_validates_size():
    encoder = codecs.getincrementalencoder('euc_jp')()
    pending_size_nine = int.from_bytes(
        b"\x09"
        b"\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00",
        'little')
    pytest.raises(UnicodeError, encoder.setstate, pending_size_nine)


def test_encoder_setstate_validates_utf8():
    encoder = codecs.getincrementalencoder('euc_jp')()
    invalid_utf8 = int.from_bytes(
        b"\x01" b"\xff" b"\x00\x00\x00\x00\x00\x00\x00\x00",
        'little')
    pytest.raises(UnicodeDecodeError, encoder.setstate, invalid_utf8)


def test_decoder_setstate_validates_pending_size():
    decoder = codecs.getincrementaldecoder('euc_jp')()
    pytest.raises(UnicodeError, decoder.setstate, (b"123456789", 0))


def test_incremental_big5hkscs():
    import _codecs
    import _io
    with open(myfile + '/big5hkscs.txt', 'rb') as fid:
        uni_str = fid.read()
    with open(myfile + '/big5hkscs-utf8.txt', 'rb') as fid:
        utf8str = fid.read()
    UTF8Reader = _codecs.lookup('utf-8').streamreader
    for sizehint in [None] + list(range(1, 33)) + [64, 128, 256, 512, 1024]:
        istream = UTF8Reader(_io.BytesIO(utf8str))
        ostream = _io.BytesIO()
        encoder = IncrementalBig5hkscsEncoder()
        while 1:
            if sizehint is not None:
                data = istream.read(sizehint)
            else:
                data = istream.read()
            if not data:
                break
            e = encoder.encode(data)
            ostream.write(e)
        assert ostream.getvalue() == uni_str

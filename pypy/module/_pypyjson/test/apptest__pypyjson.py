# -*- coding: utf-8 -*-
# spaceconfig = {"usemodules": ["_pypyjson"]}
"""App-level tests for _pypyjson.make_encoder / W_Encoder."""
import _pypyjson
import json.encoder as je

# fast_encode_mode constants (must match interp_encoder.py)
FAST_ENCODE_ASCII   = 0
FAST_ENCODE_UNICODE = 1
FAST_ENCODE_CUSTOM  = 2


def _make_encoder(ensure_ascii=True, sort_keys=False, skipkeys=False,
                  allow_nan=True):
    encoder = je.encode_basestring_ascii if ensure_ascii else je.encode_basestring
    return _pypyjson.make_encoder(
        None, je.JSONEncoder().default, encoder, None,
        ': ', ', ', sort_keys, skipkeys, allow_nan)


def test_fast_encode_mode_ascii():
    # make_encoder must identify encode_basestring_ascii (mode 0).
    # Non-ASCII chars must be escaped as \uXXXX.
    enc = _make_encoder(ensure_ascii=True)
    assert enc.fast_encode_mode == FAST_ENCODE_ASCII
    assert ''.join(enc(u'\u03b1', 0)) == '"\\u03b1"'


def test_fast_encode_mode_unicode():
    # make_encoder must identify encode_basestring (mode 1).
    # Non-ASCII chars must pass through unchanged.
    enc = _make_encoder(ensure_ascii=False)
    assert enc.fast_encode_mode == FAST_ENCODE_UNICODE
    assert ''.join(enc(u'\u03b1', 0)) == u'"\u03b1"'


def test_fast_encode_mode_custom():
    # An unrecognised callable sets mode 2 and is called per string.
    called = []
    def my_encoder(s):
        called.append(s)
        return '"custom"'
    enc = _pypyjson.make_encoder(
        None, je.JSONEncoder().default, my_encoder, None,
        ': ', ', ', False, False, True)
    assert enc.fast_encode_mode == FAST_ENCODE_CUSTOM
    assert ''.join(enc(u'hello', 0)) == '"custom"'
    assert called == [u'hello']


def test_encode_truefalse_sort_keys():
    # Bool keys must sort by their JSON string form ("false" < "true").
    enc = _make_encoder(sort_keys=True)
    assert ''.join(enc({True: False, False: True}, 0)) == '{"false": true, "true": false}'


def test_encode_sort_keys_by_value():
    # Mixed numeric keys must sort by original value, not by JSON string form.
    # "false" > "6" lexicographically, but False(0) < 2 < 4.0 < 6 numerically.
    enc = _make_encoder(sort_keys=True)
    result = ''.join(enc({2: 3.0, 4.0: 5, False: 1, 6: True}, 0))
    assert result == '{"false": 1, "2": 3.0, "4.0": 5, "6": true}', result


def test_encode_mutated_list():
    # Mutations to a list during default() must be visible (lazy iteration,
    # matching CPython's enumerate() behaviour).
    a = [object()] * 10
    def crasher(obj):
        del a[-1]
    enc = _pypyjson.make_encoder(
        None, crasher, je.encode_basestring_ascii, None,
        ': ', ', ', False, False, True)
    assert ''.join(enc(a, 0)) == '[null, null, null, null, null]'


def test_encode_non_ascii_unicode():
    # ensure_ascii=False must pass non-ASCII chars through unchanged.
    enc = _make_encoder(ensure_ascii=False)
    u = u'\u03b1\u03a9'
    assert ''.join(enc([u], 0)) == u'["' + u + u'"]'

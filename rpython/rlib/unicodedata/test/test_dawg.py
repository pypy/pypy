import pytest
from hypothesis import given, strategies

from rpython.rlib.unicodedata.dawg import Dawg, lookup, inverse_lookup, build_compression_dawg, _inverse_lookup
from rpython.rlib.unicodedata.dawg import encode_varint_unsigned, decode_varint_unsigned

def test_0():
    dawg = Dawg()
    dawg.insert("a", 0)
    dawg.insert("ac", 1)
    dawg.finish()
    assert dawg.inverse_lookup(0) == "a"
    assert dawg.inverse_lookup(1) == "ac"

def test_1():
    dawg = Dawg()
    dawg.insert("a", -4)
    dawg.insert("c", -2)
    dawg.insert("cat", -1)
    dawg.insert("catarr", 0)
    dawg.insert("catnip", 1)
    dawg.insert("zcatnip", 5)
    packed, data = dawg.finish()
    assert dawg.lookup("a") == -4
    assert dawg.lookup("c") == -2
    assert dawg.lookup("cat") == -1
    assert dawg.lookup("catarr") == 0
    assert dawg.lookup("catnip") == 1
    assert dawg.lookup("zcatnip") == 5
    assert dawg.inverse_lookup(-4) == "a"
    assert dawg.inverse_lookup(-2) == "c"
    assert dawg.inverse_lookup(-1) == "cat"
    assert dawg.inverse_lookup(0) == "catarr"
    assert dawg.inverse_lookup(1) == "catnip"
    assert dawg.inverse_lookup(5) == "zcatnip"

    assert lookup(packed, data, "a") == -4
    assert lookup(packed, data, "c") == -2
    assert lookup(packed, data, "cat") == -1
    assert lookup(packed, data, "catarr") == 0
    assert lookup(packed, data, "catnip") == 1
    assert lookup(packed, data, "zcatnip") == 5
    assert inverse_lookup(packed, dawg.inverse, -4) == "a"
    assert inverse_lookup(packed, dawg.inverse, -2) == "c"
    assert inverse_lookup(packed, dawg.inverse, -1) == "cat"
    assert inverse_lookup(packed, dawg.inverse, 0) == "catarr"
    assert inverse_lookup(packed, dawg.inverse, 1) == "catnip"
    assert inverse_lookup(packed, dawg.inverse, 5) == "zcatnip"

def test_2():
    dawg = Dawg()
    dawg.insert("aaaaaa", -2)
    dawg.insert("baaaaa", -4)
    dawg.insert("bbbbbaaaaaaa", 0)
    dawg.insert("bbbbbbbbb", -1)
    packed, data = dawg.finish()

def test_missing_key_inverse():
    dawg = Dawg()
    dawg.insert("aaaaaa", -2)
    dawg.insert("baaaaa", -4)
    dawg.insert("bbbbbaaaaaaa", 0)
    dawg.insert("bbbbbbbbb", -1)
    packed, data = dawg.finish()
    with pytest.raises(KeyError):
        _inverse_lookup(packed, 5)

def test_generate():
    import py
    tmpdir = py.test.ensuretemp(__name__)
    lines = lines = map(hex,map(hash, map(str, range(100))))
    # some extra handcrafted tests
    lines.extend([ 'AAA', 'AAAA', 'AAAB', 'AAB', 'AABB' ]) 
    out = tmpdir.join('dawg.py')
    print(out)
    o = out.open('w')
    trie = build_compression_dawg(
        o, dict(map(lambda (x,y):(y,x), enumerate(lines))))
    o.close()
    dmod = out.pyimport()
    for i, line in enumerate(lines):
        assert dmod.lookup_charcode(i) == line
        assert dmod.dawg_lookup(line) == i


@given(strategies.integers(min_value=0), strategies.binary())
def test_varint_hypothesis(i, prefix):
    b = []
    encode_varint_unsigned(i, b)
    b = b"".join(b)
    res, pos = decode_varint_unsigned(b)
    assert res == i
    assert pos == len(b)
    res, pos = decode_varint_unsigned(prefix + b, len(prefix))
    assert res == i
    assert pos == len(b) + len(prefix)


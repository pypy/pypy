import pytest
from hypothesis import given, strategies

from rpython.rlib.unicodedata.dawg import (Dawg, lookup, inverse_lookup,
        build_compression_dawg, _inverse_lookup,
        encode_varint_unsigned, decode_varint_unsigned,
        number_add_bits, number_split_bits)
from rpython.rlib.unicodedata.codegen import CodeWriter

def test_1():
    dawg = Dawg()
    dawg.insert("a", -4)
    dawg.insert("c", -2)
    dawg.insert("cat", -1)
    dawg.insert("catarr", 0)
    dawg.insert("catnip", 1)
    dawg.insert("zcatnip", 5)
    packed, data, inverse = dawg.finish()

    assert lookup(packed, data, "a") == -4
    assert lookup(packed, data, "c") == -2
    assert lookup(packed, data, "cat") == -1
    assert lookup(packed, data, "catarr") == 0
    assert lookup(packed, data, "catnip") == 1
    assert lookup(packed, data, "zcatnip") == 5
    assert inverse_lookup(packed, inverse, -4) == "a"
    assert inverse_lookup(packed, inverse, -2) == "c"
    assert inverse_lookup(packed, inverse, -1) == "cat"
    assert inverse_lookup(packed, inverse, 0) == "catarr"
    assert inverse_lookup(packed, inverse, 1) == "catnip"
    assert inverse_lookup(packed, inverse, 5) == "zcatnip"

def test_2():
    dawg = Dawg()
    dawg.insert("aaaaaa", -2)
    dawg.insert("baaaaa", -4)
    dawg.insert("bbbbbaaaaaaa", 0)
    dawg.insert("bbbbbbbbb", -1)
    packed, data, inverse = dawg.finish()

def test_bug_match_past_string_end():
    dawg = Dawg()
    dawg.insert("a", -2)
    dawg.insert("ba", 2)
    packed, data, inverse = dawg.finish()
    with pytest.raises(KeyError):
        lookup(packed, data, "b")

def test_bug_1():
    dawg = Dawg()
    dawg.insert("a", -2)
    dawg.insert("aa", 2)
    dawg.insert("b", 56)
    packed, data, inverse = dawg.finish()
    with pytest.raises(KeyError):
        lookup(packed, data, "ba")

def test_missing_key_inverse():
    dawg = Dawg()
    dawg.insert("aaaaaa", -2)
    dawg.insert("baaaaa", -4)
    dawg.insert("bbbbbaaaaaaa", 0)
    dawg.insert("bbbbbbbbb", -1)
    packed, data, inverse = dawg.finish()
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
    d = dict(map(lambda (x,y):(y,x), enumerate(lines)))
    trie = build_compression_dawg(CodeWriter(o), d)
    o.close()
    print out.read()
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

@given(strategies.integers())
def test_add_bits(i):
    for bit1, bit2 in ((0, 0), (0, 1), (1, 0), (1, 1)):
        assert number_split_bits(number_add_bits(i, bit1, bit2), 2) == (i, bit1, bit2)


START = ord('A')
STOP = ord('G')

@given(strategies.lists(strategies.text(strategies.characters(min_codepoint=START, max_codepoint=STOP), min_size=1), min_size=5), strategies.data())
def test_random_dawg(l, data):
    l = [s.encode('ascii') for s in l]
    print l

    d = {s: i for i, s in enumerate(l)}
    tmpdir = pytest.ensuretemp(__name__)
    out = tmpdir.join('%s.py' % hash(str(l)))
    o = out.open('w')
    print "&~" * 50
    print l
    trie = build_compression_dawg(CodeWriter(o), d)
    o.close()
    s = out.read()
    dmod = {}
    exec s in dmod
    dawg_lookup = dmod['dawg_lookup']
    lookup_charcode = dmod['lookup_charcode']
    def near_misses(s):
        for replacement_char in range(START, STOP):
            replacement_char = chr(replacement_char)
            yield s + replacement_char
            yield replacement_char + s
            for pos in range(len(s)):
                news = s[:pos] + replacement_char + s[pos + 1:]
                yield news
    for s, i in d.items():
        assert dawg_lookup(s) == d[s]
        assert lookup_charcode(i) == s

        # check some near misses
        for news in near_misses(s):
            if news in d:
                continue
            with pytest.raises(KeyError):
                dawg_lookup(news)
    valid_values = {i for s, i in d.items()}
    for i in range(-100, len(l) + 100):
        if i in valid_values:
            continue
        with pytest.raises(KeyError):
            lookup_charcode(i)

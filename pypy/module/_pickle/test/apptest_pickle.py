import pytest
from _pickle import Pickler, PicklingError, dumps
from _pickle import Unpickler, UnpicklingError, loads
import pickle
from pickle import _dumps as dumps_py
import sys

protocols = range(5, -1, -1)

def test_int():
    for proto in protocols:
        n = sys.maxsize
        while n:
            for expected in (-n, n):
                s = dumps(expected, proto)
                s2 = pickle._dumps(expected, proto)
                print(expected, proto, s)
                if s != s2:
                    print(s, s2)
                assert s == s2
                n2 = loads(s)
                assert expected == n2
                n = n >> 1

def test_ints():
    for proto in protocols:
        n = sys.maxsize
        while n:
            for expected in (-n, n):
                s1= dumps(expected, proto)
                s2 = dumps_py(expected, proto)
                assert s1 == s2
                n2 = loads(s1)
                assert expected == n2, "expected %d got %d for protocol %d" %(expected, n2, proto)
            n = n >> 1


def test_long():
    for proto in protocols:
        # 256 bytes is where LONG4 begins.
        for nbits in 1, 8, 8*254, 8*255, 8*256, 8*257:
            nbase = 1 << nbits
            for npos in nbase-1, nbase, nbase+1:
                for n in npos, -npos:
                    pickle = dumps(n, proto)
                    got = loads(pickle)
                    assert n == got
    # Try a monster.  This is quadratic-time in protos 0 & 1, so don't
    # bother with those.
    nbase = int("deadbeeffeedface", 16)
    nbase += nbase << 1000000
    for n in nbase, -nbase:
        p = dumps(n, 2)
        got = loads(p)
        assert n == got


def test_none_true_false():
    s = dumps(None)
    assert s == b'\x80\x04N.'
    assert loads(s) is None
    s = dumps(True)
    assert s == b'\x80\x04\x88.'
    assert loads(s) is True
    s = dumps(False)
    assert s == b'\x80\x04\x89.'
    assert loads(s) is False

def test_bytes():
    s = dumps(b'abc')
    assert s == b'\x80\x04C\x03abc\x94.'
    assert loads(s) == b"abc"
    s = dumps(b'abc' * 1000)
    assert s.startswith(b'\x80\x04B\xb8\x0b\x00\x00abcab')
    assert loads(s) == b"abc" * 1000
    s = dumps(b'abc' * 1000000)
    assert s.startswith(b'\x80\x04B\xc0\xc6-\x00abcabcabc')
    assert loads(s) == b"abc" * 1000000

def test_unicode():
    s = dumps(u'abc')
    assert s == b'\x80\x04\x8c\x03abc\x94.'
    assert loads(s) == u"abc"
    s = dumps(u'abc' * 1000)
    assert s.startswith(b'\x80\x04X\xb8\x0b\x00\x00abcabcabc')
    assert loads(s) == u"abc" * 1000
    s = dumps(u'abc' * 100000)
    assert s.startswith(b'\x80\x04X\xe0\x93\x04\x00abcabcabc')
    assert loads(s) == u'abc' * 100000

def test_tuple():
    s = dumps(())
    assert s == b'\x80\x04).'
    assert loads(s) == ()
    s = dumps((1, ))
    assert s.startswith(b'\x80\x04K\x01\x85\x94.')
    assert loads(s) == (1,)
    s = dumps((1, ) * 1000)
    assert s.startswith(b'\x80\x04(K\x01K\x01K')
    assert loads(s) == (1, ) * 1000

def test_memo():
    a = "abcdefghijkl"
    s = dumps((a, a))
    assert s.count(b'abcdefghijkl') == 1
    assert loads(s) == (a, a)
    a = (1, )
    s = dumps((a, a))
    assert s.count(b'K\x01\x85') == 1
    assert loads(s) == (a, a)

def test_list():
    s = dumps([])
    assert s == b'\x80\x04]\x94.'
    assert loads(s) == []
    s = dumps([1])
    assert s == b'\x80\x04]\x94K\x01a.'
    assert loads(s) == [1]
    s = dumps([1] * 1000)
    assert s.startswith(b'\x80\x04]\x94(K\x01K\x01K\x01K\x01K\x01K\x01K')
    assert loads(s) == [1] * 1000

def test_list_memo():
    l = []
    l.append(l)
    s = dumps(l)
    assert s == b'\x80\x04]\x94h\x00a.'
    l_roundtrip = loads(s)
    # the comparision fails untranslated
    # assert l_roundtrip == l

    t = (1, 2, 3, [], "abc")
    t[3].append(t)
    s = dumps(t)
    assert s == b'\x80\x04(K\x01K\x02K\x03]\x94(K\x01K\x02K\x03h\x00\x8c\x03abc\x94t\x94ah\x011h\x02.'
    t_roundtrip = loads(s)
    # the comparision fails untranslated
    # assert t_roundtrip == t

def test_dict():
    s = dumps({})
    assert s == b'\x80\x04}\x94.'
    assert loads(s) == {}
    s = dumps({1: 2})
    assert s == b'\x80\x04}\x94K\x01K\x02s.'
    assert loads(s) == {1: 2}
    d = dict([(a, str(a)) for a in range(10000)])
    s = dumps(d)
    assert s.startswith(b'\x80\x04}\x94(K\x00\x8c\x010\x94K\x01\x8c\x011\x94K\x02')
    assert loads(s) == d

def test_reduce():
    import sys
    class A:
        pass

    mod = type(sys)('fakemod')
    mod.A = A
    A.__module__ = 'fakemod'
    A.__qualname__ = 'A'
    A.__name__ = 'A'

    sys.modules['fakemod'] = mod
    try:

        a = A()
        a.x = 'abc'
        s = dumps(a)
        assert s == b'\x80\x04\x8c\x07fakemod\x94\x8c\x01A\x94\x93\x94)\x81\x94}\x94\x8c\x01x\x94\x8c\x03abc\x94sb.'
        a_roundtrip = loads(s)
        assert type(a_roundtrip) == type(a)
        assert a_roundtrip.x == "abc"
    finally:
        del sys.modules['fakemod']

def test_globals():
    s = dumps(dumps)
    assert s == b'\x80\x04\x8c\x07_pickle\x94\x8c\x05dumps\x94\x93\x94.'
    assert loads(s) == dumps

def test_float():
    s = dumps(1.234)
    assert s == b'\x80\x04G?\xf3\xbev\xc8\xb49X.'
    assert loads(s) == 1.234

def test_frozenset():
    f = frozenset((1, 2, 3))
    s = dumps(f)
    assert pickle.FROZENSET in s
    f2 = loads(s)
    assert isinstance(f2, frozenset)
    assert f == f2

def test_bytearray():
    for proto in protocols:
        for s in b'', b'xyz', b'xyz'*100:
            b = bytearray(s)
            p = dumps(b, proto)
            print(b, p, proto)
            bb = loads(p)
            assert bb is not b
            assert b == bb
            if proto <= 3:
                # bytearray is serialized using a global reference
                assert b'bytearray' in p
                assert pickle.GLOBAL in p
            elif proto == 4:
                assert b'bytearray' in p
                assert pickle.STACK_GLOBAL in p
            elif proto == 5:
                assert b'bytearray' not in p
                assert pickle.BYTEARRAY8 in p

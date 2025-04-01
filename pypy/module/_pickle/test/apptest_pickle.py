import pytest
from _pickle import Pickler, PicklingError, dumps
from _pickle import Unpickler, UnpicklingError, loads
import pickle

def test_int():
    s = dumps(12)
    assert s == b'\x80\x04K\x0c.'
    assert loads(s) == 12
    s = dumps(1024)
    assert s == b'\x80\x04M\x00\x04.'
    assert loads(s) == 1024
    s = dumps(-1024)
    assert s == b'\x80\x04J\x00\xfc\xff\xff.'
    assert loads(s) == -1024
    s = dumps(2**32)
    assert s == b'\x80\x04\x8a\x05\x00\x00\x00\x00\x01.'
    assert loads(s) == 2**32
    s = dumps(-3**19999)
    assert s.startswith(b'\x80\x04\x8b{\x0f\x00\x00\xd5\xcd\xc3\x89\xb1\x86$f\xe8+p\x1c@Y')
    assert loads(s) == -3**19999

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

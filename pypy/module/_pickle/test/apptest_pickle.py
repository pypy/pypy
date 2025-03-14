import pytest
from _pickle import Pickler, PicklingError, dumps
from _pickle import Unpickler, UnpicklingError, loads

def test_save_int():
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

def test_save_none_true_false():
    s = dumps(None)
    assert s == b'\x80\x04N.'
    assert loads(s) is None
    s = dumps(True)
    assert s == b'\x80\x04\x88.'
    assert loads(s) is True
    s = dumps(False)
    assert s == b'\x80\x04\x89.'
    assert loads(s) is False

def test_save_bytes():
    s = dumps(b'abc')
    assert s == b'\x80\x04C\x03abc\x94.'
    s = dumps(b'abc' * 1000)
    assert s.startswith(b'\x80\x04B\xb8\x0b\x00\x00abcab')
    s = dumps(b'abc' * 1000000)
    assert s.startswith(b'\x80\x04B\xc0\xc6-\x00abcabcabc')

def test_save_unicode():
    s = dumps(u'abc')
    assert s == b'\x80\x04\x8c\x03abc\x94.'
    s = dumps(u'abc' * 1000)
    assert s.startswith(b'\x80\x04X\xb8\x0b\x00\x00abcabcabc')
    s = dumps(u'abc' * 100000)
    assert s.startswith(b'\x80\x04X\xe0\x93\x04\x00abcabcabc')

def test_save_tuple():
    s = dumps(())
    assert s == b'\x80\x04).'
    s = dumps((1, ))
    assert s.startswith(b'\x80\x04K\x01\x85\x94.')
    s = dumps((1, ) * 1000)
    assert s.startswith(b'\x80\x04(K\x01K\x01K')

def test_memo():
    a = "abcdefghijkl"
    s = dumps((a, a))
    assert s.count(b'abcdefghijkl') == 1
    a = (1, )
    s = dumps((a, a))
    assert s.count(b'K\x01\x85') == 1

def test_save_list():
    s = dumps([])
    assert s == b'\x80\x04]\x94.'
    s = dumps([1])
    assert s == b'\x80\x04]\x94K\x01a.'
    s = dumps([1] * 1000)
    assert s.startswith(b'\x80\x04]\x94(K\x01K\x01K\x01K\x01K\x01K\x01K')

def test_save_list_memo():
    l = []
    l.append(l)
    s = dumps(l)
    assert s == b'\x80\x04]\x94h\x00a.'

    t = (1, 2, 3, [], "abc")
    t[3].append(t)
    s = dumps(t)
    assert s == b'\x80\x04(K\x01K\x02K\x03]\x94(K\x01K\x02K\x03h\x00\x8c\x03abc\x94t\x94ah\x011h\x02.'

def test_save_dict():
    s = dumps({})
    assert s == b'\x80\x04}\x94.'
    s = dumps({1: 2})
    assert s == b'\x80\x04}\x94K\x01K\x02s.'
    s = dumps(dict([(a, str(a)) for a in range(10000)]))
    assert s.startswith(b'\x80\x04}\x94(K\x00\x8c\x010\x94K\x01\x8c\x011\x94K\x02')

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
    finally:
        del sys.modules['fakemod']

def test_globals():
    s = dumps(dumps)
    assert s == b'\x80\x04\x8c\x07_pickle\x94\x8c\x05dumps\x94\x93\x94.'

def test_save_float():
    s = dumps(1.234)
    assert s == b'\x80\x04G?\xf3\xbev\xc8\xb49X.'

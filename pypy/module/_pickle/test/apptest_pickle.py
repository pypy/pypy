import pytest
from _pickle import Pickler, PicklingError, dumps

def test_save_int():
    s = dumps(12)
    assert s == b'\x80\x04K\x0c.'
    s = dumps(1024)
    assert s == b'\x80\x04M\x00\x04.'
    s = dumps(-1024)
    assert s == b'\x80\x04J\x00\xfc\xff\xff.'
    s = dumps(2**32)
    assert s == b'\x80\x04\x8a\x05\x00\x00\x00\x00\x01.'
    s = dumps(-3**19999)
    assert s.startswith(b'\x80\x04\x8b{\x0f\x00\x00\xd5\xcd\xc3\x89\xb1\x86$f\xe8+p\x1c@Y')

def test_save_none_true_false():
    s = dumps(None)
    assert s == b'\x80\x04N.'
    s = dumps(True)
    assert s == b'\x80\x04\x88.'
    s = dumps(False)
    assert s == b'\x80\x04\x89.'

def test_save_bytes():
    s = dumps(b'abc')
    assert s == b'\x80\x04C\x03abc.'
    s = dumps(b'abc' * 1000)
    assert s.startswith(b'\x80\x04B\xb8\x0b\x00\x00abcab')
    s = dumps(b'abc' * 1000000)
    assert s.startswith(b'\x80\x04B\xc0\xc6-\x00abcabcabc')

def test_save_unicode():
    s = dumps(u'abc')
    assert s == b'\x80\x04\x8c\x03abc.'
    s = dumps(u'abc' * 1000)
    assert s.startswith(b'\x80\x04X\xb8\x0b\x00\x00abcabcabc')
    s = dumps(u'abc' * 100000)
    assert s.startswith(b'\x80\x04X\xe0\x93\x04\x00abcabcabc')

def test_save_tuple():
    s = dumps(())
    assert s == b'\x80\x04).'
    s = dumps((1, ))
    assert s.startswith(b'\x80\x04K\x01\x85.')
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
    assert s ==  b'\x80\x04]\x94.'
    s = dumps([1])
    assert s == b'\x80\x04]\x94K\x01a.'
    s = dumps([1] * 1000)
    assert s.startswith(b'\x80\x04]\x94(K\x01K\x01K\x01K\x01K\x01K\x01K')


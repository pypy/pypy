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

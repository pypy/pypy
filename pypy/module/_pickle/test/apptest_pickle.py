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

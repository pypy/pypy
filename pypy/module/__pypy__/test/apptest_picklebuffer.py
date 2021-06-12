import pytest
from __pypy__ import PickleBuffer

def test_basics():
    pb = PickleBuffer(b"foo")
    assert b"foo" == bytes(pb)
    with memoryview(pb) as m:
        assert m.readonly

    pb = PickleBuffer(bytearray(b"foo"))
    assert bytes(pb) == b"foo"
    with memoryview(pb) as m:
        assert not m.readonly
        m[0] = ord("b")

    assert bytes(pb) == b"boo"

def test_relase():
    pb = PickleBuffer(b"foo")
    pb.release()
    with pytest.raises(ValueError):
        memoryview(pb)
    pb.release()

def test_weakref():
    import _weakref, gc
    pb = PickleBuffer(b"foo")
    w = _weakref.ref(pb)
    assert w() is pb
    pb = None
    gc.collect()
    assert w() is None

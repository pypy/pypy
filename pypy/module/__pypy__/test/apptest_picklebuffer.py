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

def test_memoryobject_picklebuffer_gives_obj_back():
    b = b"abc"
    pb = PickleBuffer(b)
    m = memoryview(pb)
    assert m.obj is b


def test_picklebuffer_holds_bytearray_export():
    # A live PickleBuffer must lock the bytearray (prevent resize).
    import gc
    b = bytearray(b'hello')
    pb = PickleBuffer(b)
    try:
        b += b'!'
    except BufferError:
        pass
    else:
        raise AssertionError("expected BufferError while PickleBuffer alive")
    pb.release()
    b += b'!'   # must succeed after explicit release


def test_picklebuffer_gc_releases_bytearray_export():
    # Bug 1: W_PickleBuffer defines _finalize_ but never calls
    # register_finalizer.  A PickleBuffer GC'd without explicit release leaks
    # _exports and leaves the bytearray permanently locked.
    import gc
    b = bytearray(b'hello')
    pb = PickleBuffer(b)
    try:
        b += b'!'   # must raise: PickleBuffer still alive
    except BufferError:
        pass
    else:
        raise AssertionError("expected BufferError while PickleBuffer alive")

    del pb
    gc.collect()
    gc.collect()   # FinalizerQueue may need a second cycle
    b += b'!'   # must NOT raise: GC must have released the export

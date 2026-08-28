"""
App-level tests for buffer/memoryview export tracking.
"""
import gc


def test_slice_does_not_double_release():
    # Slicing a memoryview must not create additional owning references to the
    # bytearray export.  When the slices are GC'd, _exports must not underflow.
    b = bytearray(b'hello world')
    m = memoryview(b)
    s1 = m[:5]
    s2 = m[6:]
    s3 = s1[1:]   # slice of slice
    # b is still locked
    raises(BufferError, b.append, ord('!'))
    # releasing all views (explicit)
    s3.release()
    s2.release()
    s1.release()
    # b still locked because m holds the export
    raises(BufferError, b.append, ord('!'))
    m.release()
    # now unlocked
    b.append(ord('!'))
    assert b == bytearray(b'hello world!')


def test_slice_gc_does_not_crash():
    # GC-collecting sliced memoryviews must not crash (assertion failure in
    # BytearrayBuffer.releasebuffer due to _exports underflow).
    b = bytearray(b'abcdef')
    m = memoryview(b)
    s1 = m[:4]
    s2 = m[2:]
    s3 = s1[1:3]
    del s1, s2, s3, m
    gc.collect()
    # if we get here without crashing, the fix is good
    b.append(ord('g'))
    assert b == bytearray(b'abcdefg')


def test_slice_gc_cycle():
    # Reference cycle involving sliced memoryviews must break cleanly.
    import weakref

    class Box:
        pass

    class Wrapper:
        pass

    b = bytearray(b'XabcdefY')
    m = memoryview(b)
    sliced = m[:7][1:]   # two levels of slicing
    o = Box()
    w = Wrapper()
    w.m = sliced         # wrapper holds sliced
    w.o = o              # wrapper holds o -> cycle: w.m.w_obj -> b; b not in cycle
    wr = weakref.ref(o)
    del m, sliced, o, w
    gc.collect()
    gc.collect()
    assert wr() is None, "cycle not broken"
    b.append(ord('Z'))
    assert b[-1] == ord('Z')


def test_re_finditer_keeps_buffer():
    # Replica of lib-python test.test_re.ReTests.test_keep_buffer (bug 14212):
    # a running re.finditer over a bytearray must hold a buffer export,
    # preventing modification of the bytearray until the iterator is exhausted
    # and collected.
    import re
    b = bytearray(b'x')
    it = re.finditer(b'a', b)
    raises(BufferError, b.extend, b'x' * 400)
    list(it)
    del it
    gc.collect()
    b.extend(b'x' * 400)  # must succeed now


def test_original_release_then_slice_gc():
    # Releasing the original memoryview (decrementing _exports) and then
    # GC-ing the surviving slices must be a no-op for the slices.
    import weakref

    b = bytearray(b'hello')
    m = memoryview(b)
    s = m[:3]
    m.release()         # releases the export: _exports -> 0
    b.append(ord('!'))  # must work: export is gone
    del s
    gc.collect()        # GC of s must not crash
    b.append(ord('?'))
    assert b == bytearray(b'hello!?')

    # matches CPython's test_memoryview.py::test_use_released_memory: a
    # __index__ callback that releases the memoryview mid-slice must not
    # break the resulting slice, since it is built from the buffer view
    # captured before the index was decoded.  Plain (non-slice) indexing,
    # by contrast, must re-check released-ness after decoding the index
    # and raise.
    size = 128

    class MyIndex:
        def __index__(self):
            m.release()
            return 4

    m = memoryview(bytearray(b'\xff' * size))
    raises(ValueError, lambda: m[MyIndex()])

    m = memoryview(bytearray(b'\xff' * size))
    assert list(m[:MyIndex()]) == [255] * 4

    m = memoryview(bytearray(b'\xff' * size))
    assert list(m[MyIndex():8]) == [255] * 4


def test_release_saves_reference():
    # matches CPython's test_buffer.py::test_release_saves_reference: while
    # __release_buffer__ is running, the memoryview it receives must reject
    # new buffer exports (new memoryview / cast / toreadonly / slice /
    # explicit __buffer__ call) with ValueError, even though direct data
    # access (tobytes) on it still works.
    import pytest

    smuggled_buffer = None

    class C(bytearray):
        def __release_buffer__(s, buffer):
            with pytest.raises(ValueError):
                memoryview(buffer)
            with pytest.raises(ValueError):
                buffer.cast("b")
            with pytest.raises(ValueError):
                buffer.toreadonly()
            with pytest.raises(ValueError):
                buffer[:1]
            with pytest.raises(ValueError):
                buffer.__buffer__(0)
            nonlocal smuggled_buffer
            smuggled_buffer = buffer
            assert buffer.tobytes() == b"hello"
            super(C, s).__release_buffer__(buffer)

    c = C(b"hello")
    with memoryview(c) as mv:
        assert mv.tobytes() == b"hello"
    c.clear()
    with pytest.raises(ValueError):
        smuggled_buffer.tobytes()


def test_strided_double_slice_tobytes():
    # issue 5231: slicing an already-strided memoryview must offset by the
    # parent's step, so tobytes() matches element-by-element indexing.
    mv = memoryview(bytes(range(256)))
    size = 8
    bs = [mv[boffset::size] for boffset in range(size)]
    for L in range(0, 32):
        for R in range(L, 32):
            for boffset in range(size):
                mybs = bs[boffset]
                way1 = bytes(mybs[i] for i in range(L, R))
                way2 = mybs[L:R].tobytes()
                assert way1 == way2, (boffset, L, R, way1, way2)

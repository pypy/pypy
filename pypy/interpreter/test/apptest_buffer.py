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

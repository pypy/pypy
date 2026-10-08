"""App-level tests for memoryview."""
from pytest import raises


def test_setitem_released_during_value_conversion():
    # gh-92888: memoryview must re-check if view was released after
    # converting the value via __index__, before writing.
    size = 128

    def release():
        m.release()

    class MyIndex:
        def __index__(self):
            release()
            return 4

    m = memoryview(bytearray(b'\xff' * size))
    with raises(ValueError, match="operation forbidden"):
        m[0] = MyIndex()


def test_setitem_released_during_value_conversion_formats():
    size = 128

    def release():
        m.release()

    class MyIndex:
        def __index__(self):
            release()
            return 4

    for fmt in 'bhilqnBHILQN':
        m = memoryview(bytearray(b'\xff' * size)).cast(fmt)
        with raises(ValueError, match="operation forbidden"):
            m[0] = MyIndex()


def test_setitem_released_during_float_conversion():
    size = 128

    def release():
        m.release()

    class MyFloat:
        def __float__(self):
            release()
            return 4.25

    for fmt in 'fd':
        m = memoryview(bytearray(b'\xff' * size)).cast(fmt)
        with raises(ValueError, match="operation forbidden"):
            m[0] = MyFloat()


def test_setitem_released_during_bool_conversion():
    size = 128

    def release():
        m.release()

    class MyBool:
        def __bool__(self):
            release()
            return True

    m = memoryview(bytearray(b'\xff' * size)).cast('?')
    with raises(ValueError, match="operation forbidden"):
        m[0] = MyBool()


def test_tuple_setitem_released_during_value_conversion():
    size = 128

    def release():
        m.release()

    class MyIndex:
        def __index__(self):
            release()
            return 4

    m = memoryview(bytearray(b'\xff' * size)).cast('B', (64, 2))
    with raises(ValueError, match="operation forbidden"):
        m[0, 0] = MyIndex()


def test_cast_bytearray_exports_balanced():
    # Regression: memoryview(bytearray(...)).cast('I') used to underflow
    # the bytearray's _exports counter when both memoryviews were GCed,
    # triggering an RPython AssertionError in BytearrayBuffer.releasebuffer.
    # Minimal reproducer of the `re.compile(r'[a-z]', re.I)` crash via
    # re/_compiler.py: `memoryview(b).cast('I')`.
    import gc
    b = bytearray(256)
    mv = memoryview(b).cast('I')
    del mv
    for _ in range(3):
        gc.collect()
    # After gc, the bytearray must be unlocked (exports back to 0)
    # and resizable again.
    b.append(1)
    assert len(b) == 257


def test_toreadonly_does_not_release_underlying_export():
    # Regression: memoryview(bytearray).toreadonly() followed by bytes()
    # used to decrement the bytearray's _exports counter via the non-owning
    # buffer_w path, causing a double-release when the original memoryview
    # was later finalized.
    b = bytearray(b'hello')
    mv = memoryview(b)      # acquires export; b is now locked
    ro = mv.toreadonly()    # derived non-owning view; must not add a new export

    data = bytes(ro)        # reads ro as a buffer; must NOT release b's export
    assert data == b'hello'

    # mv still holds the export so b must still be locked
    try:
        b.append(0)
        assert False, "BufferError expected: mv still holds the export"
    except BufferError:
        pass

    del ro
    del mv
    import gc
    gc.collect()
    b.append(0)             # now free
    assert b == bytearray(b'hello\x00')


def test_struct_unpack_from_cast_memoryview_slice():
    # Regression: struct.unpack_from failed with TypeError on a slice of a
    # cast memoryview because BufferSlice.as_writebuf() raised
    # BufferInterfaceNotFound (inherited from BufferView base class).
    import struct
    b = bytearray(b'\x01\x00\x02\x00')
    mv = memoryview(b).cast('H')   # 2 unsigned-short items
    sl_bytes = memoryview(b)[0:2]  # byte slice of original
    assert sl_bytes.format == 'B'
    result = struct.unpack_from('H', sl_bytes)
    assert result == (1,)


def test_derived_views_keep_the_export():
    # issue 5613: a slice, cast or copy keeps the memoryview that owns the
    # export alive, so that a GC can't release the export while it is in use
    import gc
    b = bytearray(b'abcdefgh')
    views = [memoryview(b)[2:], memoryview(b).cast('B', [2, 4]),
             memoryview(memoryview(b)), memoryview(b).toreadonly(),
             memoryview(b)[1:][1:]]
    gc.collect()
    gc.collect()
    with raises(BufferError):
        b.clear()
    assert bytes(views[0]) == b'cdefgh'
    assert views[1][1, 3] == ord('h')
    assert bytes(views[4]) == b'cdefgh'
    del views
    gc.collect()
    gc.collect()
    b.clear()


def test_derived_views_of_released_view():
    # issue 5613: releasing the memoryview that owns the export releases it
    # at once, and the views derived from it count as released too, instead
    # of using the buffer after it is resized
    b = bytearray(b'abcdefgh')
    m = memoryview(b)
    derived = [m[2:], m.cast('B', [2, 4]), memoryview(m), m.toreadonly(),
               m[1:][1:]]
    m.release()
    b.clear()
    for v in derived:
        with raises(ValueError, match="operation forbidden"):
            v.tobytes()
        with raises(ValueError, match="operation forbidden"):
            memoryview(v)
        with raises(ValueError, match="operation forbidden"):
            v._pypy_raw_address()
        assert 'released memory' in repr(v)
        assert v != memoryview(b'')
        assert memoryview(b'') != v
    with raises(ValueError, match="operation forbidden"):
        derived[1][1, 3] = 0
    for v in derived:
        v.release()


def test_derived_views_of_released_bytes_view():
    # releasing a memoryview of bytes releases nothing, so the views
    # derived from it stay usable, as on CPython
    m = memoryview(b'abcdefgh')
    s = m[2:]
    c = m.cast('B', [2, 4])
    m.release()
    assert bytes(s) == b'cdefgh'
    assert c[1, 3] == ord('h')


def test_compare_with_released_view():
    m = memoryview(b'ab')
    r = memoryview(b'ab')
    r.release()
    assert not m == r
    assert m != r
    assert not r == m


def test_cast_released_during_shape_conversion():
    class Two:
        def __index__(self):
            m.release()
            return 2
    m = memoryview(bytearray(8))
    # CPython raises TypeError, as it accepts only ints in the shape
    with raises((TypeError, ValueError)):
        m.cast('B', [Two(), 4])

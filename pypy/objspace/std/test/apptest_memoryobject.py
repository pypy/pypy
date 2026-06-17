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



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


def test_python_buffer_protocol_basic():
    class MyBuffer:
        def __buffer__(self, flags):
            return memoryview(b"hello")

    mv = memoryview(MyBuffer())
    assert mv.tobytes() == b"hello"
    assert bytes(MyBuffer()) == b"hello"


def test_python_buffer_protocol_release_buffer():
    class WhatToRelease:
        def __init__(self):
            self.held = False
            self.ba = bytearray(b"hello")

        def __buffer__(self, flags):
            if self.held:
                raise TypeError("already held")
            self.held = True
            return memoryview(self.ba)

        def __release_buffer__(self, buffer):
            self.held = False

    wr = WhatToRelease()
    assert not wr.held
    with memoryview(wr) as mv:
        assert wr.held
        assert mv.tobytes() == b"hello"
    assert not wr.held


def test_python_buffer_protocol_same_buffer_returned():
    class WhatToRelease:
        def __init__(self):
            self.held = False
            self.ba = bytearray(b"hello")
            self.created_mv = None

        def __buffer__(self, flags):
            if self.held:
                raise TypeError("already held")
            self.held = True
            self.created_mv = memoryview(self.ba)
            return self.created_mv

        def __release_buffer__(self, buffer):
            assert buffer is self.created_mv
            self.held = False

    wr = WhatToRelease()
    with memoryview(wr) as mv:
        assert mv.tobytes() == b"hello"
    assert not wr.held


def test_memoryview_from_flags():
    import inspect

    class PossiblyMutable:
        def __init__(self, data, mutable):
            self._data = bytearray(data)
            self._mutable = mutable

        def __buffer__(self, flags):
            if flags & inspect.BufferFlags.WRITABLE:
                if not self._mutable:
                    raise RuntimeError("not mutable")
                return memoryview(self._data)
            else:
                return memoryview(bytes(self._data))

    mutable = PossiblyMutable(b"hello", True)
    immutable = PossiblyMutable(b"hello", False)
    with memoryview._from_flags(mutable, inspect.BufferFlags.WRITABLE) as mv:
        assert mv.tobytes() == b"hello"
        mv[0] = ord(b'x')
        assert mv.tobytes() == b"xello"
    with memoryview._from_flags(mutable, inspect.BufferFlags.SIMPLE) as mv:
        assert mv.tobytes() == b"xello"
        with raises(TypeError):
            mv[0] = ord(b'h')
    with raises(RuntimeError):
        memoryview._from_flags(immutable, inspect.BufferFlags.WRITABLE)


def test_bytearray_dunder_buffer_direct():
    import sys
    ba = bytearray(b"hello")
    mv = ba.__buffer__(0)
    assert mv.tobytes() == b"hello"
    ba.__release_buffer__(mv)
    with raises(OverflowError):
        ba.__buffer__(sys.maxsize + 1)


def test_bytearray_subclass_inherits_buffer():
    class A(bytearray):
        def __buffer__(self, flags):
            return super().__buffer__(flags)

    a = A(b"hello")
    mv = memoryview(a)
    assert mv.tobytes() == b"hello"


def test_bytearray_subclass_inheritance_releasebuffer():
    rb_call_count = [0]

    class B(bytearray):
        def __buffer__(self, flags):
            return super().__buffer__(flags)

        def __release_buffer__(self, view):
            rb_call_count[0] += 1
            super().__release_buffer__(view)

    b = B(b"hello")
    with memoryview(b) as mv:
        assert mv.tobytes() == b"hello"
        assert rb_call_count[0] == 0
    assert rb_call_count[0] == 1


def test_bytearray_subclass_inherit_but_return_something_else():
    rb_call_count = [0]
    rb_raised = [False]

    class B(bytearray):
        def __buffer__(self, flags):
            return memoryview(b"hello")

        def __release_buffer__(self, view):
            rb_call_count[0] += 1
            try:
                super().__release_buffer__(view)
            except ValueError:
                rb_raised[0] = True

    b = B(b"hello")
    with memoryview(b) as mv:
        assert mv.tobytes() == b"hello"
        assert rb_call_count[0] == 0
    assert rb_call_count[0] == 1
    assert rb_raised[0] is True


def test_bytearray_subclass_override_only_release():
    class C(bytearray):
        def __release_buffer__(self, buffer):
            super().__release_buffer__(buffer)

    c = C(b"hello")
    with memoryview(c) as mv:
        assert mv.tobytes() == b"hello"


def test_bytearray_subclass_release_saves_reference_no_subclassing():
    ba = bytearray(b"hello")

    class C:
        def __buffer__(self, flags):
            return memoryview(ba)

        def __release_buffer__(self, buffer):
            self.buffer = buffer

    c = C()
    with memoryview(c) as mv:
        assert mv.tobytes() == b"hello"
    assert c.buffer.tobytes() == b"hello"

    with raises(BufferError):
        ba.clear()
    c.buffer.release()
    ba.clear()


def test_bytearray_subclass_multiple_inheritance_buffer_last():
    class A:
        def __buffer__(self, flags):
            return memoryview(b"hello A")

    class B(A, bytearray):
        def __buffer__(self, flags):
            return super().__buffer__(flags)

    b = B(b"hello")
    with memoryview(b) as mv:
        assert mv.tobytes() == b"hello A"

    class Releaser:
        def __release_buffer__(self, buffer):
            self.buffer = buffer

    class C(Releaser, bytearray):
        def __buffer__(self, flags):
            return super().__buffer__(flags)

    c = C(b"hello C")
    with memoryview(c) as mv:
        assert mv.tobytes() == b"hello C"
    c.clear()
    with raises(ValueError):
        c.buffer.tobytes()


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


def test_bytes_dunder_buffer_direct():
    b = b"hello"
    mv = b.__buffer__(0)
    assert type(mv) is memoryview
    assert mv.tobytes() == b"hello"
    assert mv.readonly


def test_memoryview_dunder_buffer_direct():
    orig = memoryview(b"hello")
    mv = orig.__buffer__(0)
    assert type(mv) is memoryview
    assert mv is not orig
    assert mv.tobytes() == b"hello"



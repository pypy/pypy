class AppTestMemoryView:
    spaceconfig = dict(usemodules=['array'])

    def test_basic(self):
        v = memoryview(b"abc")
        assert v.tobytes() == b"abc"
        assert len(v) == 3
        assert v[0] == ord('a')
        assert list(v) == [97, 98, 99]
        assert v.tolist() == [97, 98, 99]
        assert v[1] == ord("b")
        assert v[-1] == ord("c")
        exc = raises(TypeError, "v[1] = b'x'")
        assert str(exc.value) == "cannot modify read-only memory"
        assert v.readonly is True
        w = v[1:234]
        assert isinstance(w, memoryview)
        assert len(w) == 2
        exc = raises(NotImplementedError, "v[0:2:2]")
        assert str(exc.value) == ""
        exc = raises(TypeError, "memoryview('foobar')")

    def test_rw(self):
        data = bytearray(b'abcefg')
        v = memoryview(data)
        assert v.readonly is False
        v[0] = ord('z')
        assert data == bytearray(eval("b'zbcefg'"))
        v[1:4] = b'123'
        assert data == bytearray(eval("b'z123fg'"))
        v[0:3] = v[2:5]
        assert data == bytearray(eval("b'23f3fg'"))
        exc = raises(ValueError, "v[2:3] = b'spam'")
        assert str(exc.value) == "cannot modify size of memoryview object"
        exc = raises(NotImplementedError, "v[0:2:2] = b'spam'")
        assert str(exc.value) == ""

    def test_memoryview_attrs(self):
        v = memoryview(b"a"*100)
        assert v.format == "B"
        assert v.itemsize == 1
        assert v.shape == (100,)
        assert v.ndim == 1
        assert v.strides == (1,)

    def test_suboffsets(self):
        v = memoryview(b"a"*100)
        assert v.suboffsets == ()

    def test_compare(self):
        assert memoryview(b"abc") == b"abc"
        assert memoryview(b"abc") == bytearray(b"abc")
        assert memoryview(b"abc") != 3
        assert memoryview(b'ab') == b'ab'
        assert b'ab' == memoryview(b'ab')
        assert not (memoryview(b'ab') != b'ab')
        assert memoryview(b'ab') == memoryview(b'ab')
        assert not (memoryview(b'ab') != memoryview(b'ab'))
        assert memoryview(b'ab') != memoryview(b'abc')
        raises(TypeError, "memoryview(b'ab') <  memoryview(b'ab')")
        raises(TypeError, "memoryview(b'ab') <= memoryview(b'ab')")
        raises(TypeError, "memoryview(b'ab') >  memoryview(b'ab')")
        raises(TypeError, "memoryview(b'ab') >= memoryview(b'ab')")
        raises(TypeError, "memoryview(b'ab') <  memoryview(b'abc')")
        raises(TypeError, "memoryview(b'ab') <= memoryview(b'ab')")
        raises(TypeError, "memoryview(b'ab') >  memoryview(b'aa')")
        raises(TypeError, "memoryview(b'ab') >= memoryview(b'ab')")

    def test_array_buffer(self):
        import array
        b = memoryview(array.array("B", [1, 2, 3]))
        assert len(b) == 3
        assert b[0:3] == b"\x01\x02\x03"

    def test_nonzero(self):
        assert memoryview(b'\x00')
        assert not memoryview(b'')
        import array
        assert memoryview(array.array("B", [0]))
        assert not memoryview(array.array("B", []))

    def test_bytes(self):
        assert bytes(memoryview(b'hello')) == b'hello'

    def test_repr(self):
        assert repr(memoryview(b'hello')).startswith('<memory at 0x')

    def test_hash(self):
        assert hash(memoryview(b'hello')) == hash(b'hello')

    def test_weakref(self):
        import weakref
        m = memoryview(b'hello')
        weakref.ref(m)

    def test_getitem_only_ints(self):
        class MyInt(object):
          def __init__(self, x):
            self.x = x

          def __int__(self):
            return self.x

        buf = memoryview(b'hello world')
        raises(TypeError, "buf[MyInt(0)]")
        raises(TypeError, "buf[MyInt(0):MyInt(5)]")

    def test_release(self):
        v = memoryview(b"a"*100)
        v.release()
        raises(ValueError, len, v)
        raises(ValueError, v.tolist)
        raises(ValueError, v.tobytes)
        raises(ValueError, "v[0]")
        raises(ValueError, "v[0] = b'a'")
        raises(ValueError, "v.format")
        raises(ValueError, "v.itemsize")
        raises(ValueError, "v.ndim")
        raises(ValueError, "v.readonly")
        raises(ValueError, "v.shape")
        raises(ValueError, "v.strides")
        raises(ValueError, "v.suboffsets")
        raises(ValueError, "with v as cm: pass")
        raises(ValueError, "memoryview(v)")
        assert v == v
        assert v != memoryview(b"a"*100)
        assert v != b"a"*100
        assert "released memory" in repr(v)

    def test_context_manager(self):
        v = memoryview(b"a"*100)
        with v as cm:
            assert cm is v
        raises(ValueError, bytes, v)
        assert "released memory" in repr(v)

    def test_int_array_buffer(self):
        import array
        m = memoryview(array.array('i', list(range(10))))
        assert m.format == 'i'
        assert m.itemsize == 4
        assert len(m) == 10
        assert len(m.tobytes()) == 40
        assert m[0] == 0
        m[0] = 1
        assert m[0] == 1

    def test_int_array_slice(self):
        import array
        m = memoryview(array.array('i', list(range(10))))
        slice = m[2:8]
        assert slice.format == 'i'
        assert slice.itemsize == 4
        assert len(slice) == 6
        assert len(slice.tobytes()) == 24
        assert slice[0] == 2
        slice[0] = 1
        assert slice[0] == 1
        assert m[2] == 1

    def test_pypy_raw_address_base(self):
        raises(ValueError, memoryview(b"foobar")._pypy_raw_address)
        a = memoryview(bytearray(b"foobar"))._pypy_raw_address()
        assert a != 0

    def test_hex(self):
        assert memoryview(b"abc").hex() == u'616263'

    @py.test.skip("needs numpy ndarray")
    def test_tuple_indexing(self):
        content = ndarray(list(range(12)))
        assert memoryview(content)[0,0] == 0

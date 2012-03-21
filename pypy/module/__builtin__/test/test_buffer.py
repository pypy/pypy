"""Tests some behaviour of the buffer type that is not tested in
lib-python/2.5.2/test/test_types.py where the stdlib buffer tests live."""
import autopath
from pypy.conftest import gettestobjspace

class AppTestMemoryView:

    spaceconfig = dict(usemodules=['array'])

    def test_basic(self):
        v = memoryview(b"abc")
        assert v.tobytes() == b"abc"
        assert len(v) == 3
        assert list(v) == [b'a', b'b', b'c']
        assert v.tolist() == [97, 98, 99]
        assert v[1] == b"b"
        assert v[-1] == b"c"
        raises(TypeError, "v[1] = 'x'")
        assert v.readonly is True
        w = v[1:234]
        assert isinstance(w, memoryview)
        assert len(w) == 2

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

    def test_compare(self):
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

    def test_hash(self):
        raises(TypeError, "hash(memoryview(b'hello'))")

    def test_rw(self):
        data = bytearray(b'abcefg')
        v = memoryview(data)
        assert v.readonly is False
        v[0] = b'z'
        assert data == bytearray(eval("b'zbcefg'"))
        v[1:4] = b'123'
        assert data == bytearray(eval("b'z123fg'"))
        raises((ValueError, TypeError), "v[2] = 'spam'")

    def test_memoryview_attrs(self):
        v = memoryview(b"a"*100)
        assert v.format == "B"
        assert v.itemsize == 1
        assert v.shape == (100,)
        assert v.ndim == 1
        assert v.strides == (1,)

    def test_suboffsets(self):
        v = memoryview(b"a"*100)
        assert v.suboffsets == None

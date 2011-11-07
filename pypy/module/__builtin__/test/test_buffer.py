"""Tests some behaviour of the buffer type that is not tested in
lib-python/2.5.2/test/test_types.py where the stdlib buffer tests live."""
import autopath
from pypy.conftest import gettestobjspace

class AppTestBuffer:
    spaceconfig = dict(usemodules=['array'])

    def test_unicode_buffer(self):
        import sys
        b = buffer(u"ab")
        if sys.maxunicode == 65535: # UCS2 build
            assert len(b) == 4
            if sys.byteorder == "big":
                assert b[0:4] == b"\x00a\x00b"
            else:
                assert b[0:4] == b"a\x00b\x00"
        else: # UCS4 build
            assert len(b) == 8
            if sys.byteorder == "big":
                assert b[0:8] == b"\x00\x00\x00a\x00\x00\x00b"
            else:
                assert b[0:8] == b"a\x00\x00\x00b\x00\x00\x00"

    def test_array_buffer(self):
        import array
        b = buffer(array.array("B", [1, 2, 3]))
        assert len(b) == 3
        assert b[0:3] == b"\x01\x02\x03"

    def test_nonzero(self):
        assert buffer('\x00')
        assert not buffer('')
        import array
        assert buffer(array.array("B", [0]))
        assert not buffer(array.array("B", []))

    def test_str(self):
        assert str(buffer(b'hello')) == 'hello'

    def test_repr(self):
        # from 2.5.2 lib tests
        assert repr(buffer(b'hello')).startswith('<read-only buffer for 0x')

    def test_add(self):
        assert buffer(b'abc') + b'def' == b'abcdef'
        import array
        assert buffer(b'abc') + array.array('b', b'def') == b'abcdef'

    def test_cmp(self):
        assert buffer(b'ab') != b'ab'
        assert not (b'ab' == buffer(b'ab'))
        assert buffer(b'ab') == buffer(b'ab')
        assert not (buffer(b'ab') != buffer(b'ab'))
        assert not (buffer(b'ab') <  buffer(b'ab'))
        assert buffer(b'ab') <= buffer(b'ab')
        assert not (buffer(b'ab') >  buffer(b'ab'))
        assert buffer(b'ab') >= buffer(b'ab')
        assert buffer(b'ab') != buffer(b'abc')
        assert buffer(b'ab') <  buffer(b'abc')
        assert buffer(b'ab') <= buffer(b'ab')
        assert buffer(b'ab') >  buffer(b'aa')
        assert buffer(b'ab') >= buffer(b'ab')

    def test_hash(self):
        assert hash(buffer(b'hello')) == hash(b'hello')

    def test_mul(self):
        assert buffer(b'ab') * 5 == b'ababababab'
        assert buffer(b'ab') * (-2) == b''
        assert 5 * buffer(b'ab') == b'ababababab'
        assert (-2) * buffer(b'ab') == b''

    def test_offset_size(self):
        b = buffer(b'hello world', 6)
        assert len(b) == 5
        assert b[0] == b'w'
        assert b[:] == b'world'
        raises(IndexError, 'b[5]')
        b = buffer(b, 2)
        assert len(b) == 3
        assert b[0] == b'r'
        assert b[:] == b'rld'
        raises(IndexError, 'b[3]')
        b = buffer(b'hello world', 1, 8)
        assert len(b) == 8
        assert b[0] == b'e'
        assert b[:] == b'ello wor'
        raises(IndexError, 'b[8]')
        b = buffer(b, 2, 3)
        assert len(b) == 3
        assert b[2] == b' '
        assert b[:] == b'lo '
        raises(IndexError, 'b[3]')
        b = buffer('hello world', 55)
        assert len(b) == 0
        assert b[:] == b''
        b = buffer(b'hello world', 6, 999)
        assert len(b) == 5
        assert b[:] == b'world'

        raises(ValueError, buffer, "abc", -1)
        raises(ValueError, buffer, "abc", 0, -2)

    def test_rw_offset_size(self):
        import array

        a = array.array("b", b'hello world')
        b = buffer(a, 6)
        assert len(b) == 5
        assert b[0] == b'w'
        assert b[:] == b'world'
        raises(IndexError, 'b[5]')
        b[0] = b'W'
        assert str(b) == b'World'
        assert a.tostring() == b'hello World'
        b[:] = b'12345'
        assert a.tostring() == b'hello 12345'
        raises(IndexError, 'b[5] = "."')

        b = buffer(b, 2)
        assert len(b) == 3
        assert b[0] == '3'
        assert b[:] == '345'
        raises(IndexError, 'b[3]')
        b[1] = 'X'
        assert a.tostring() == 'hello 123X5'
        raises(IndexError, 'b[3] = "."')

        a = array.array("c", 'hello world')
        b = buffer(a, 1, 8)
        assert len(b) == 8
        assert b[0] == 'e'
        assert b[:] == 'ello wor'
        raises(IndexError, 'b[8]')
        b[0] = 'E'
        assert str(b) == 'Ello wor'
        assert a.tostring() == 'hEllo world'
        b[:] = '12345678'
        assert a.tostring() == 'h12345678ld'
        raises(IndexError, 'b[8] = "."')

        b = buffer(b, 2, 3)
        assert len(b) == 3
        assert b[2] == '5'
        assert b[:] == '345'
        raises(IndexError, 'b[3]')
        b[1] = 'X'
        assert a.tostring() == 'h123X5678ld'
        raises(IndexError, 'b[3] = "."')

        b = buffer(a, 55)
        assert len(b) == 0
        assert b[:] == ''
        b = buffer(a, 6, 999)
        assert len(b) == 5
        assert b[:] == '678ld'

        raises(ValueError, buffer, a, -1)
        raises(ValueError, buffer, a, 0, -2)

    def test_slice(self):
        # Test extended slicing by comparing with list slicing.
        s = bytes(c for c in list(range(255, -1, -1)))
        b = buffer(s)
        indices = (0, None, 1, 3, 19, 300, -1, -2, -31, -300)
        for start in indices:
            for stop in indices:
                # Skip step 0 (invalid)
                for step in indices[1:]:
                    assert b[start:stop:step] == s[start:stop:step]

class AppTestMemoryView:
    def test_basic(self):
        v = memoryview(b"abc")
        assert v.tobytes() == b"abc"
        assert len(v) == 3
        assert list(v) == ['a', 'b', 'c']
        assert v.tolist() == [97, 98, 99]
        assert v[1] == "b"
        assert v[-1] == "c"
        raises(TypeError, "v[1] = 'x'")
        assert v.readonly is True
        w = v[1:234]
        assert isinstance(w, memoryview)
        assert len(w) == 2

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
        v = memoryview(buffer(b"a"*100, 2))
        assert v.shape == (98,)
        assert v.suboffsets == None

    def test_compare(self):
        assert memoryview(b"abc") == b"abc"
        assert memoryview(b"abc") == bytearray(b"abc")
        assert memoryview(b"abc") != 3

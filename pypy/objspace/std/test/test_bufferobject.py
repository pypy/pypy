class AppTestBuffer:
    spaceconfig = dict(usemodules=['array'])

    def test_init(self):
        import sys
        class A(object):
            def __buffer__(self, flags):
                return buffer('123')
        if '__pypy__' not in sys.builtin_module_names:
            raises(TypeError, buffer, A())
        else:
            assert buffer(A()) == buffer('123')

    def test_unicode_buffer(self):
        import sys
        b = buffer(u"ab")
        if sys.maxunicode == 65535: # UCS2 build
            assert len(b) == 4
            if sys.byteorder == "big":
                assert b[0:4] == "\x00a\x00b"
            else:
                assert b[0:4] == "a\x00b\x00"
        else: # UCS4 build
            assert len(b) == 8
            if sys.byteorder == "big":
                assert b[0:8] == "\x00\x00\x00a\x00\x00\x00b"
            else:
                assert b[0:8] == "a\x00\x00\x00b\x00\x00\x00"

    def test_array_buffer(self):
        import array
        b = buffer(array.array("B", [1, 2, 3]))
        assert len(b) == 3
        assert b[0:3] == "\x01\x02\x03"

    def test_nonzero(self):
        assert buffer('\x00')
        assert not buffer('')
        import array
        assert buffer(array.array("B", [0]))
        assert not buffer(array.array("B", []))

    def test_str(self):
        assert str(buffer('hello')) == 'hello'

    def test_repr(self):
        # from 2.5.2 lib tests
        assert repr(buffer('hello')).startswith('<read-only buffer for 0x')

    def test_add(self):
        assert buffer('abc') + 'def' == 'abcdef'
        import array
        assert buffer('abc') + array.array('c', 'def') == 'abcdef'

    def test_cmp(self):
        assert buffer('ab') != 'ab'
        assert not ('ab' == buffer('ab'))
        assert buffer('ab') == buffer('ab')
        assert not (buffer('ab') != buffer('ab'))
        assert not (buffer('ab') <  buffer('ab'))
        assert buffer('ab') <= buffer('ab')
        assert not (buffer('ab') >  buffer('ab'))
        assert buffer('ab') >= buffer('ab')
        assert buffer('ab') != buffer('abc')
        assert buffer('ab') <  buffer('abc')
        assert buffer('ab') <= buffer('ab')
        assert buffer('ab') >  buffer('aa')
        assert buffer('ab') >= buffer('ab')

    def test_hash(self):
        assert hash(buffer('hello')) == hash('hello')

    def test_mul(self):
        assert buffer('ab') * 5 == 'ababababab'
        assert buffer('ab') * (-2) == ''
        assert 5 * buffer('ab') == 'ababababab'
        assert (-2) * buffer('ab') == ''

    def test_offset_size(self):
        b = buffer('hello world', 6)
        assert len(b) == 5
        assert b[0] == 'w'
        assert b[:] == 'world'
        raises(IndexError, 'b[5]')
        b = buffer(b, 2)
        assert len(b) == 3
        assert b[0] == 'r'
        assert b[:] == 'rld'
        raises(IndexError, 'b[3]')
        b = buffer('hello world', 1, 8)
        assert len(b) == 8
        assert b[0] == 'e'
        assert b[:] == 'ello wor'
        raises(IndexError, 'b[8]')
        b = buffer(b, 2, 3)
        assert len(b) == 3
        assert b[2] == ' '
        assert b[:] == 'lo '
        raises(IndexError, 'b[3]')
        b = buffer('hello world', 55)
        assert len(b) == 0
        assert b[:] == ''
        b = buffer('hello world', 6, 999)
        assert len(b) == 5
        assert b[:] == 'world'

        raises(ValueError, buffer, "abc", -1)
        raises(ValueError, buffer, "abc", 0, -2)

    def test_rw_offset_size(self):
        import array

        a = array.array("c", 'hello world')
        b = buffer(a, 6)
        assert len(b) == 5
        assert b[0] == 'w'
        assert b[:] == 'world'
        raises(IndexError, 'b[5]')
        exc = raises(TypeError, "b[0] = 'W'")
        assert str(exc.value) == "buffer is read-only"
        exc = raises(TypeError, "b[:] = '12345'")
        assert str(exc.value) == "buffer is read-only"
        exc = raises(TypeError, 'b[5] = "."')
        assert str(exc.value) == "buffer is read-only"
        exc = raises(TypeError, "b[4:2] = ''")
        assert str(exc.value) == "buffer is read-only"
        assert str(b) == 'world'
        assert a.tostring() == 'hello world'

        b = buffer(b, 2)
        assert len(b) == 3
        assert b[0] == 'r'
        assert b[:] == 'rld'
        raises(IndexError, 'b[3]')
        exc = raises(TypeError, "b[1] = 'X'")
        assert str(exc.value) == "buffer is read-only"
        exc = raises(TypeError, 'b[3] = "."')
        assert str(exc.value) == "buffer is read-only"
        assert a.tostring() == 'hello world'

        a = array.array("c", 'hello world')
        b = buffer(a, 1, 8)
        assert len(b) == 8
        assert b[0] == 'e'
        assert b[:] == 'ello wor'
        raises(IndexError, 'b[8]')
        exc = raises(TypeError, "b[0] = 'E'")
        assert str(exc.value) == "buffer is read-only"
        assert str(b) == 'ello wor'
        assert a.tostring() == 'hello world'
        exc = raises(TypeError, "b[:] = '12345678'")
        assert str(exc.value) == "buffer is read-only"
        assert a.tostring() == 'hello world'
        exc = raises(TypeError, 'b[8] = "."')
        assert str(exc.value) == "buffer is read-only"

        b = buffer(b, 2, 3)
        assert len(b) == 3
        assert b[2] == ' '
        assert b[:] == 'lo '
        raises(IndexError, 'b[3]')
        exc = raises(TypeError, "b[1] = 'X'")
        assert str(exc.value) == "buffer is read-only"
        assert a.tostring() == 'hello world'
        exc = raises(TypeError, 'b[3] = "."')
        assert str(exc.value) == "buffer is read-only"

        b = buffer(a, 55)
        assert len(b) == 0
        assert b[:] == ''
        b = buffer(a, 6, 999)
        assert len(b) == 5
        assert b[:] == 'world'

        raises(ValueError, buffer, a, -1)
        raises(ValueError, buffer, a, 0, -2)

    def test_slice(self):
        # Test extended slicing by comparing with list slicing.
        s = "".join(chr(c) for c in list(range(255, -1, -1)))
        b = buffer(s)
        indices = (0, None, 1, 3, 19, 300, -1, -2, -31, -300)
        for start in indices:
            for stop in indices:
                # Skip step 0 (invalid)
                for step in indices[1:]:
                    assert b[start:stop:step] == s[start:stop:step]

    def test_getitem_only_ints(self):
        class MyInt(object):
          def __init__(self, x):
            self.x = x

          def __int__(self):
            return self.x

        buf = buffer('hello world')
        raises(TypeError, "buf[MyInt(0)]")
        raises(TypeError, "buf[MyInt(0):MyInt(5)]")

    def test_pypy_raw_address_base(self):
        a = buffer("foobar")._pypy_raw_address()
        assert a != 0
        b = buffer(u"foobar")._pypy_raw_address()
        assert b != 0
        c = buffer(bytearray("foobar"))._pypy_raw_address()
        assert c != 0

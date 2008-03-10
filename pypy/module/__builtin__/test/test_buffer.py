"""Tests some behaviour of the buffer type that is not tested in
lib-python/2.4.1/test/test_types.py where the stdlib buffer tests live."""
import autopath

class AppTestBuffer:

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

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

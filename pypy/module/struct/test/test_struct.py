"""
Tests for the struct module implemented at interp-level in pypy/module/struct.
"""

import py
from pypy.conftest import gettestobjspace
from pypy.module.struct.nativefmttable import native_is_bigendian


class AppTestStruct(object):

    def setup_class(cls):
        """
        Create a space with the struct module and import it for use by the
        tests.
        """
        cls.space = gettestobjspace(usemodules=['struct'])
        cls.w_struct = cls.space.appexec([], """():
            import struct
            return struct
        """)
        cls.w_native_is_bigendian = cls.space.wrap(native_is_bigendian)


    def test_error(self):
        """
        struct.error should be an exception class.
        """
        assert issubclass(self.struct.error, Exception)


    def test_calcsize_standard(self):
        """
        Check the standard size of the various format characters.
        """
        calcsize = self.struct.calcsize
        assert calcsize('=') == 0
        assert calcsize('<x') == 1
        assert calcsize('>c') == 1
        assert calcsize('!b') == 1
        assert calcsize('=B') == 1
        assert calcsize('<h') == 2
        assert calcsize('>H') == 2
        assert calcsize('!i') == 4
        assert calcsize('=I') == 4
        assert calcsize('<l') == 4
        assert calcsize('>L') == 4
        assert calcsize('!q') == 8
        assert calcsize('=Q') == 8
        assert calcsize('<f') == 4
        assert calcsize('>d') == 8
        assert calcsize('!13s') == 13
        assert calcsize('=500p') == 500
        # test with some repetitions and multiple format characters
        assert calcsize('=bQ3i') == 1 + 8 + 3*4


    def test_pack_standard_little(self):
        """
        Check packing with the '<' format specifier.
        """
        pack = self.struct.pack
        assert pack("<i", 0x41424344) == 'DCBA'
        assert pack("<i", -3) == '\xfd\xff\xff\xff'
        assert pack("<i", -2147483648) == '\x00\x00\x00\x80'


    def test_unpack_standard_little(self):
        """
        Check unpacking with the '<' format specifier.
        """
        unpack = self.struct.unpack
        assert unpack("<i", 'DCBA') == (0x41424344,)
        assert unpack("<i", '\xfd\xff\xff\xff') == (-3,)
        assert unpack("<i", '\x00\x00\x00\x80') == (-2147483648,)


    def test_calcsize_native(self):
        """
        Check that the size of the various format characters is reasonable.
        """
        calcsize = self.struct.calcsize
        assert calcsize('') == 0
        assert calcsize('x') == 1
        assert calcsize('c') == 1
        assert calcsize('b') == 1
        assert calcsize('B') == 1
        assert (2 <= calcsize('h') == calcsize('H')
                  <  calcsize('i') == calcsize('I')
                  <= calcsize('l') == calcsize('L')
                  <= calcsize('q') == calcsize('Q'))
        assert 4 <= calcsize('f') <= 8 <= calcsize('d')
        assert calcsize('13s') == 13
        assert calcsize('500p') == 500
        assert 4 <= calcsize('P') <= 8
        # test with some repetitions and multiple format characters
        assert 4 + 8 + 3*4 <= calcsize('bQ3i') <= 8 + 8 + 3*8
        # test alignment
        assert calcsize('bi') == calcsize('ii') == 2 * calcsize('i')
        assert calcsize('bbi') == calcsize('ii') == 2 * calcsize('i')
        assert calcsize('hi') == calcsize('ii') == 2 * calcsize('i')


    def test_pack_native(self):
        """
        Check packing with the native format.
        """
        pack = self.struct.pack
        sizeofi = self.struct.calcsize("i")
        res = pack("bi", -2, 5)
        assert len(res) == 2 * sizeofi
        assert res[0] == '\xfe'
        assert res[1:sizeofi] == '\x00' * (sizeofi-1)    # padding
        if self.native_is_bigendian:
            assert res[sizeofi:] == '\x00' * (sizeofi-1) + '\x05'
        else:
            assert res[sizeofi:] == '\x05' + '\x00' * (sizeofi-1)


    def test_unpack_native(self):
        """
        Check unpacking with the native format.
        """
        pack = self.struct.pack
        unpack = self.struct.unpack
        assert unpack("bi", pack("bi", -2, 5)) == (-2, 5)


    def test_string_format(self):
        """
        Check the 's' format character.
        """
        pack = self.struct.pack
        unpack = self.struct.unpack
        assert pack("7s", "hello") == "hello\x00\x00"
        assert pack("5s", "world") == "world"
        assert pack("3s", "spam") == "spa"
        assert pack("0s", "foo") == ""
        assert unpack("7s", "hello\x00\x00") == ("hello\x00\x00",)
        assert unpack("5s3s", "worldspa") == ("world", "spa")
        assert unpack("0s", "") == ("",)


    def test_pascal_format(self):
        """
        Check the 'p' format character.
        """
        pack = self.struct.pack
        unpack = self.struct.unpack
        longstring = str(range(70))     # this has 270 chars
        longpacked300 = "\xff" + longstring + "\x00" * (299-len(longstring))
        assert pack("8p", "hello") == "\x05hello\x00\x00"
        assert pack("6p", "world") == "\x05world"
        assert pack("4p", "spam") == "\x03spa"
        assert pack("1p", "foo") == "\x00"
        assert pack("10p", longstring) == "\x09" + longstring[:9]
        assert pack("300p", longstring) == longpacked300
        assert unpack("8p", "\x05helloxx") == ("hello",)
        assert unpack("5p", "\x80abcd") == ("abcd",)
        assert unpack("1p", "\x03") == ("",)
        assert unpack("300p", longpacked300) == (longstring[:255],)


    def test_char_format(self):
        """
        Check the 'c' format character.
        """
        pack = self.struct.pack
        unpack = self.struct.unpack
        assert pack("c", "?") == "?"
        assert pack("5c", "a", "\xc0", "\x00", "\n", "-") == "a\xc0\x00\n-"
        assert unpack("c", "?") == ("?",)
        assert unpack("5c", "a\xc0\x00\n-") == ("a", "\xc0", "\x00", "\n", "-")


    def test_pad_format(self):
        """
        Check the 'x' format character.
        """
        pack = self.struct.pack
        unpack = self.struct.unpack
        assert pack("x") == "\x00"
        assert pack("5x") == "\x00" * 5
        assert unpack("x", "?") == ()
        assert unpack("5x", "hello") == ()

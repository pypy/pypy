"""
Tests for the struct module implemented at interp-level in pypy/module/struct.
"""

import py
from pypy.conftest import gettestobjspace
from pypy.rlib.rstruct.nativefmttable import native_is_bigendian


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
        assert pack("<I", 0x81424344) == 'DCB\x81'
        assert pack("<q", 0x4142434445464748) == 'HGFEDCBA'
        assert pack("<q", -0x41B2B3B4B5B6B7B8) == 'HHIJKLM\xbe'
        assert pack("<Q", 0x8142434445464748) == 'HGFEDCB\x81'


    def test_unpack_standard_little(self):
        """
        Check unpacking with the '<' format specifier.
        """
        unpack = self.struct.unpack
        assert unpack("<i", 'DCBA') == (0x41424344,)
        assert unpack("<i", '\xfd\xff\xff\xff') == (-3,)
        assert unpack("<i", '\x00\x00\x00\x80') == (-2147483648,)
        assert unpack("<I", 'DCB\x81') == (0x81424344,)
        assert unpack("<q", 'HGFEDCBA') == (0x4142434445464748,)
        assert unpack("<q", 'HHIJKLM\xbe') == (-0x41B2B3B4B5B6B7B8,)
        assert unpack("<Q", 'HGFEDCB\x81') == (0x8142434445464748,)


    def test_pack_standard_big(self):
        """
        Check packing with the '>' format specifier.
        """
        pack = self.struct.pack
        assert pack(">i", 0x41424344) == 'ABCD'
        assert pack(">i", -3) == '\xff\xff\xff\xfd'
        assert pack(">i", -2147483648) == '\x80\x00\x00\x00'
        assert pack(">I", 0x81424344) == '\x81BCD'
        assert pack(">q", 0x4142434445464748) == 'ABCDEFGH'
        assert pack(">q", -0x41B2B3B4B5B6B7B8) == '\xbeMLKJIHH'
        assert pack(">Q", 0x8142434445464748) == '\x81BCDEFGH'


    def test_unpack_standard_big(self):
        """
        Check unpacking with the '>' format specifier.
        """
        unpack = self.struct.unpack
        assert unpack(">i", 'ABCD') == (0x41424344,)
        assert unpack(">i", '\xff\xff\xff\xfd') == (-3,)
        assert unpack(">i", '\x80\x00\x00\x00') == (-2147483648,)
        assert unpack(">I", '\x81BCD') == (0x81424344,)
        assert unpack(">q", 'ABCDEFGH') == (0x4142434445464748,)
        assert unpack(">q", '\xbeMLKJIHH') == (-0x41B2B3B4B5B6B7B8,)
        assert unpack(">Q", '\x81BCDEFGH') == (0x8142434445464748,)


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
        # CPython adds no padding at the end, unlike a C compiler
        assert calcsize('ib') == calcsize('i') + calcsize('b')
        assert calcsize('ibb') == calcsize('i') + 2 * calcsize('b')
        assert calcsize('ih') == calcsize('i') + calcsize('h')


    def test_pack_native(self):
        """
        Check packing with the native format.
        """
        calcsize = self.struct.calcsize
        pack = self.struct.pack
        sizeofi = calcsize("i")
        res = pack("bi", -2, 5)
        assert len(res) == 2 * sizeofi
        assert res[0] == '\xfe'
        assert res[1:sizeofi] == '\x00' * (sizeofi-1)    # padding
        if self.native_is_bigendian:
            assert res[sizeofi:] == '\x00' * (sizeofi-1) + '\x05'
        else:
            assert res[sizeofi:] == '\x05' + '\x00' * (sizeofi-1)
        assert pack("q", -1) == '\xff' * calcsize("q")


    def test_unpack_native(self):
        """
        Check unpacking with the native format.
        """
        calcsize = self.struct.calcsize
        pack = self.struct.pack
        unpack = self.struct.unpack
        assert unpack("bi", pack("bi", -2, 5)) == (-2, 5)
        assert unpack("q", '\xff' * calcsize("q")) == (-1,)


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


    def test_native_floats(self):
        """
        Check the 'd' and 'f' format characters on native packing.
        """
        calcsize = self.struct.calcsize
        pack = self.struct.pack
        unpack = self.struct.unpack
        data = pack("d", 12.34)
        assert len(data) == calcsize("d")
        assert unpack("d", data) == (12.34,)     # no precision lost
        data = pack("f", 12.34)
        assert len(data) == calcsize("f")
        res, = unpack("f", data)
        assert res != 12.34                      # precision lost
        assert abs(res - 12.34) < 1E-6


    def test_standard_floats(self):
        """
        Check the 'd' and 'f' format characters on standard packing.
        """
        pack = self.struct.pack
        unpack = self.struct.unpack
        assert pack("!d", 12.5) == '@)\x00\x00\x00\x00\x00\x00'
        assert pack("<d", -12.5) == '\x00\x00\x00\x00\x00\x00)\xc0'
        assert unpack("!d", '\xc0)\x00\x00\x00\x00\x00\x00') == (-12.5,)
        assert unpack("<d", '\x00\x00\x00\x00\x00\x00)@') == (12.5,)
        assert pack("!f", -12.5) == '\xc1H\x00\x00'
        assert pack("<f", 12.5) == '\x00\x00HA'
        assert unpack("!f", 'AH\x00\x00') == (12.5,)
        assert unpack("<f", '\x00\x00H\xc1') == (-12.5,)


    def test_struct_error(self):
        """
        Check the various ways to get a struct.error.  Note that CPython
        and PyPy might disagree on the specific exception raised in a
        specific situation, e.g. struct.error/TypeError/OverflowError.
        """
        calcsize = self.struct.calcsize
        pack = self.struct.pack
        unpack = self.struct.unpack
        error = self.struct.error
        try:
            calcsize("12")              # incomplete struct format
        except error:                   # (but ignored on CPython)
            pass
        raises(error, calcsize, "[")    # bad char in struct format
        raises(error, calcsize, "!P")   # bad char in struct format
        raises(error, pack, "ii", 15)   # struct format requires more arguments
        raises(error, pack, "i", 3, 4)  # too many arguments for struct format
        raises(error, unpack, "ii", "?")# unpack str size too short for format
        raises(error, unpack, "b", "??")# unpack str size too long for format
        raises(error, pack, "c", "foo") # expected a string of length 1
        try:
            pack("0p")                  # bad '0p' in struct format
        except error:                   # (but ignored on CPython)
            pass
        try:
            unpack("0p", "")            # bad '0p' in struct format
        except error:                   # (but ignored on CPython)
            pass
        raises(error, pack, "b", 150)   # argument out of range
        # XXX the accepted ranges still differs between PyPy and CPython


    def test_overflow_error(self):
        """
        Check OverflowError cases.
        """
        import sys
        calcsize = self.struct.calcsize
        pack = self.struct.pack
        unpack = self.struct.unpack
        someerror = (OverflowError, self.struct.error)
        raises(someerror, calcsize, "%dc" % (sys.maxint+1,))
        raises(someerror, calcsize, "999999999999999999999999999c")
        raises(someerror, calcsize, "%di" % (sys.maxint,))
        raises(someerror, calcsize, "%dcc" % (sys.maxint,))
        raises(someerror, calcsize, "c%dc" % (sys.maxint,))
        raises(someerror, calcsize, "%dci" % (sys.maxint,))


    def test_broken_input(self):
        """
        For compatibility: check that we also accept inputs that are
        wrongly accepted by CPython 2.4.
        """
        pack = self.struct.pack
        assert pack("!b", 0xa0) == '\xa0'
        assert pack("!B", -1.1) == '\xff'
        assert pack("!h", 0xa000) == '\xa0\x00'
        assert pack("!H", -2.2) == '\xff\xfe'


    def test_unicode(self):
        """
        A PyPy extension: accepts the 'u' format character in native mode,
        just like the array module does.  (This is actually used in the
        implementation of our interp-level array module.)
        """
        data = self.struct.pack("uuu", u'X', u'Y', u'Z')
        assert data == str(buffer(u'XYZ'))
        assert self.struct.unpack("uuu", data) == (u'X', u'Y', u'Z')


    def test_unpack_buffer(self):
        """
        Buffer objects can be passed to struct.unpack().
        """
        b = buffer(self.struct.pack("ii", 62, 12))
        assert self.struct.unpack("ii", b) == (62, 12)
        raises(self.struct.error, self.struct.unpack, "i", b)


class AppTestStructBuffer(object):

    def setup_class(cls):
        """
        Create a space with the struct and __pypy__ modules.
        """
        cls.space = gettestobjspace(usemodules=['struct', '__pypy__'])
        cls.w_struct = cls.space.appexec([], """():
            import struct
            return struct
        """)
        cls.w_bytebuffer = cls.space.appexec([], """():
            import __pypy__
            return __pypy__.bytebuffer
        """)

    def test_pack_into(self):
        b = self.bytebuffer(19)
        sz = self.struct.calcsize("ii")
        self.struct.pack_into("ii", b, 2, 17, 42)
        assert b[:] == ('\x00' * 2 +
                        self.struct.pack("ii", 17, 42) +
                        '\x00' * (19-sz-2))

    def test_unpack_from(self):
        b = self.bytebuffer(19)
        sz = self.struct.calcsize("ii")
        b[2:2+sz] = self.struct.pack("ii", 17, 42)
        assert self.struct.unpack_from("ii", b, 2) == (17, 42)
        b[:sz] = self.struct.pack("ii", 18, 43)
        assert self.struct.unpack_from("ii", b) == (18, 43)

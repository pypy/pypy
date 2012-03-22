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


    def test_index(self):
        class X(object):
            def __index__(self):
                return 3
        assert self.struct.unpack("i", self.struct.pack("i", X()))[0] == 3


    def test_deprecation_warning(self):
        import warnings
        for code in 'b', 'B', 'h', 'H', 'i', 'I', 'l', 'L', 'q', 'Q':
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                raises(TypeError, self.struct.pack, code, 3j)
            assert len(w) == 1
            assert str(w[0].message) == "integer argument expected, got non-integer"
            assert w[0].category is DeprecationWarning


    def test_pack_standard_little(self):
        """
        Check packing with the '<' format specifier.
        """
        pack = self.struct.pack
        assert pack("<i", 0x41424344) == b'DCBA'
        assert pack("<i", -3) == b'\xfd\xff\xff\xff'
        assert pack("<i", -2147483648) == b'\x00\x00\x00\x80'
        assert pack("<I", 0x81424344) == b'DCB\x81'
        assert pack("<q", 0x4142434445464748) == b'HGFEDCBA'
        assert pack("<q", -0x41B2B3B4B5B6B7B8) == b'HHIJKLM\xbe'
        assert pack("<Q", 0x8142434445464748) == b'HGFEDCB\x81'


    def test_unpack_standard_little(self):
        """
        Check unpacking with the '<' format specifier.
        """
        unpack = self.struct.unpack
        assert unpack("<i", b'DCBA') == (0x41424344,)
        assert unpack("<i", b'\xfd\xff\xff\xff') == (-3,)
        assert unpack("<i", b'\x00\x00\x00\x80') == (-2147483648,)
        assert unpack("<I", b'DCB\x81') == (0x81424344,)
        assert unpack("<q", b'HGFEDCBA') == (0x4142434445464748,)
        assert unpack("<q", b'HHIJKLM\xbe') == (-0x41B2B3B4B5B6B7B8,)
        assert unpack("<Q", b'HGFEDCB\x81') == (0x8142434445464748,)


    def test_pack_standard_big(self):
        """
        Check packing with the '>' format specifier.
        """
        pack = self.struct.pack
        assert pack(">i", 0x41424344) == b'ABCD'
        assert pack(">i", -3) == b'\xff\xff\xff\xfd'
        assert pack(">i", -2147483648) == b'\x80\x00\x00\x00'
        assert pack(">I", 0x81424344) == b'\x81BCD'
        assert pack(">q", 0x4142434445464748) == b'ABCDEFGH'
        assert pack(">q", -0x41B2B3B4B5B6B7B8) == b'\xbeMLKJIHH'
        assert pack(">Q", 0x8142434445464748) == b'\x81BCDEFGH'


    def test_unpack_standard_big(self):
        """
        Check unpacking with the '>' format specifier.
        """
        unpack = self.struct.unpack
        assert unpack(">i", b'ABCD') == (0x41424344,)
        assert unpack(">i", b'\xff\xff\xff\xfd') == (-3,)
        assert unpack(">i", b'\x80\x00\x00\x00') == (-2147483648,)
        assert unpack(">I", b'\x81BCD') == (0x81424344,)
        assert unpack(">q", b'ABCDEFGH') == (0x4142434445464748,)
        assert unpack(">q", b'\xbeMLKJIHH') == (-0x41B2B3B4B5B6B7B8,)
        assert unpack(">Q", b'\x81BCDEFGH') == (0x8142434445464748,)


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
        assert res[0] == 0xfe
        assert res[1:sizeofi] == b'\x00' * (sizeofi-1)    # padding
        if self.native_is_bigendian:
            assert res[sizeofi:] == b'\x00' * (sizeofi-1) + b'\x05'
        else:
            assert res[sizeofi:] == b'\x05' + b'\x00' * (sizeofi-1)
        assert pack("q", -1) == b'\xff' * calcsize("q")


    def test_unpack_native(self):
        """
        Check unpacking with the native format.
        """
        calcsize = self.struct.calcsize
        pack = self.struct.pack
        unpack = self.struct.unpack
        assert unpack("bi", pack("bi", -2, 5)) == (-2, 5)
        assert unpack("q", b'\xff' * calcsize("q")) == (-1,)


    def test_string_format(self):
        """
        Check the 's' format character.
        """
        pack = self.struct.pack
        unpack = self.struct.unpack
        assert pack("7s", b"hello") == b"hello\x00\x00"
        assert pack("5s", b"world") == b"world"
        assert pack("3s", b"spam") == b"spa"
        assert pack("0s", b"foo") == b""
        assert unpack("7s", b"hello\x00\x00") == (b"hello\x00\x00",)
        assert unpack("5s3s", b"worldspa") == (b"world", b"spa")
        assert unpack("0s", b"") == (b"",)


    def test_pascal_format(self):
        """
        Check the 'p' format character.
        """
        pack = self.struct.pack
        unpack = self.struct.unpack
        longstring = bytes(range(135)) * 2    # this has 270 chars
        longpacked300 = b"\xff" + longstring + b"\x00" * (299-len(longstring))
        assert pack("8p", b"hello") == b"\x05hello\x00\x00"
        assert pack("6p", b"world") == b"\x05world"
        assert pack("4p", b"spam") == b"\x03spa"
        assert pack("1p", b"foo") == b"\x00"
        assert pack("10p", longstring) == b"\x09" + longstring[:9]
        assert pack("300p", longstring) == longpacked300
        assert unpack("8p", b"\x05helloxx") == (b"hello",)
        assert unpack("5p", b"\x80abcd") == (b"abcd",)
        assert unpack("1p", b"\x03") == (b"",)
        assert unpack("300p", longpacked300) == (longstring[:255],)


    def test_char_format(self):
        """
        Check the 'c' format character.
        """
        pack = self.struct.pack
        unpack = self.struct.unpack
        assert pack("c", b"?") == b"?"
        assert pack("5c", b"a", b"\xc0", b"\x00", b"\n", b"-") == b"a\xc0\x00\n-"
        assert unpack("c", b"?") == (b"?",)
        assert unpack("5c", b"a\xc0\x00\n-") == (b"a", b"\xc0", b"\x00", b"\n", b"-")


    def test_pad_format(self):
        """
        Check the 'x' format character.
        """
        pack = self.struct.pack
        unpack = self.struct.unpack
        assert pack("x") == b"\x00"
        assert pack("5x") == b"\x00" * 5
        assert unpack("x", b"?") == ()
        assert unpack("5x", b"hello") == ()


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
        assert pack("!d", 12.5) == b'@)\x00\x00\x00\x00\x00\x00'
        assert pack("<d", -12.5) == b'\x00\x00\x00\x00\x00\x00)\xc0'
        assert unpack("!d", b'\xc0)\x00\x00\x00\x00\x00\x00') == (-12.5,)
        assert unpack("<d", b'\x00\x00\x00\x00\x00\x00)@') == (12.5,)
        assert pack("!f", -12.5) == b'\xc1H\x00\x00'
        assert pack("<f", 12.5) == b'\x00\x00HA'
        assert unpack("!f", b'AH\x00\x00') == (12.5,)
        assert unpack("<f", b'\x00\x00H\xc1') == (-12.5,)
        raises(OverflowError, pack, "<f", 10e100)

    def test_bool(self):
        pack = self.struct.pack
        unpack = self.struct.unpack
        assert pack("!?", True) == b'\x01'
        assert pack(">?", True) == b'\x01'
        assert pack("!?", False) == b'\x00'
        assert pack(">?", False) == b'\x00'
        assert pack("@?", True) == b'\x01'
        assert pack("@?", False) == b'\x00'

    def test_transitiveness(self):
        c = b'a'
        b = 1
        h = 255
        i = 65535
        l = 65536
        f = 3.1415
        d = 3.1415
        t = True

        for prefix in ('', '@', '<', '>', '=', '!'):
            for format in ('xcbhilfd?', 'xcBHILfd?'):
                format = prefix + format
                s = self.struct.pack(format, c, b, h, i, l, f, d, t)
                cp, bp, hp, ip, lp, fp, dp, tp = self.struct.unpack(format, s)
                assert cp == c
                assert bp == b
                assert hp == h
                assert ip == i
                assert lp == l
                assert int(100 * fp) == int(100 * f)
                assert int(100 * dp) == int(100 * d)
                assert tp == t

    def test_struct_error(self):
        """
        Check the various ways to get a struct.error.  Note that CPython
        and PyPy might disagree on the specific exception raised in a
        specific situation, e.g. struct.error/TypeError/OverflowError.
        """
        import sys
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
        raises(error, unpack, "ii", b"?")# unpack str size too short for format
        raises(error, unpack, "b", b"??")# unpack str size too long for format
        raises(error, pack, "c", b"foo") # expected a string of length 1
        try:
            pack("0p")                  # bad '0p' in struct format
        except error:                   # (but ignored on CPython)
            pass
        if '__pypy__' in sys.builtin_module_names:
            raises(error, unpack, "0p", b"")   # segfaults on CPython 2.5.2!
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


    def test_unicode(self):
        """
        A PyPy extension: accepts the 'u' format character in native mode,
        just like the array module does.  (This is actually used in the
        implementation of our interp-level array module.)
        """
        import sys
        if '__pypy__' not in sys.builtin_module_names:
            skip("PyPy extension")
        data = self.struct.pack("uuu", 'X', 'Y', 'Z')
        # this assumes UCS4; adapt/extend the test on platforms where we use
        # another format
        assert data == b'X\x00\x00\x00Y\x00\x00\x00Z\x00\x00\x00'
        assert self.struct.unpack("uuu", data) == ('X', 'Y', 'Z')


    def test_unpack_memoryview(self):
        """
        memoryview objects can be passed to struct.unpack().
        """
        b = memoryview(self.struct.pack("ii", 62, 12))
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
        assert b[:] == (b'\x00' * 2 +
                        self.struct.pack("ii", 17, 42) +
                        b'\x00' * (19-sz-2))

    def test_unpack_from(self):
        b = self.bytebuffer(19)
        sz = self.struct.calcsize("ii")
        b[2:2+sz] = self.struct.pack("ii", 17, 42)
        assert self.struct.unpack_from("ii", b, 2) == (17, 42)
        b[:sz] = self.struct.pack("ii", 18, 43)
        assert self.struct.unpack_from("ii", b) == (18, 43)

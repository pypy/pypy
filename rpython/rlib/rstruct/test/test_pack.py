import pytest
from rpython.rlib.rstruct import standardfmttable
from rpython.rlib.mutbuffer import MutableStringBuffer
import struct

class FakeFormatIter(object):

    def __init__(self, bigendian, value):
        from rpython.rlib.rstring import StringBuilder
        self.value = value
        self.bigendian = bigendian
        self.result = StringBuilder(8)

    def _accept_arg(self):
        return self.value

    def __getattr__(self, name):
        if name.startswith('accept_'):
            return self._accept_arg
        raise AttributeError(name)


class BaseTestPack(object):
    """
    These test tests only the various pack_* functions, individually.  There
    is no RPython interface to them, as for now they are used only to
    implement struct.pack in pypy/module/struct
    """

    endianess = None
    fmttable = standardfmttable.standard_fmttable

    def mypack(self, fmt, value):
        bigendian = self.endianess == '>'
        fake_fmtiter = FakeFormatIter(bigendian, value)
        attrs = self.fmttable[fmt]
        pack = attrs['pack']
        pack(fake_fmtiter)
        return fake_fmtiter.result.build()

    def check(self, fmt, value):
        expected = struct.pack(self.endianess+fmt, value)
        got = self.mypack(fmt, value)
        assert got == expected

    def test_pack_int(self):
        self.check('b', 42)
        self.check('B', 242)
        self.check('h', 32767)
        self.check('H', 32768)
        self.check("i", 0x41424344)
        self.check("i", -3)
        self.check("i", -2147483648)
        self.check("I", 0x81424344)
        self.check("q", 0x4142434445464748)
        self.check("q", -0x41B2B3B4B5B6B7B8)
        self.check("Q", 0x8142434445464748)

    def test_pack_ieee(self):
        self.check('f', 123.456)
        self.check('d', 123.456789)

    def test_pack_char(self):
        self.check('c', 'a')

    def test_pack_pad(self):
        bigendian = self.endianess == '>'
        fmtiter = FakeFormatIter(bigendian, None)
        standardfmttable.pack_pad(fmtiter, 4)
        s = fmtiter.result.build()
        assert s == '\x00'*4

    def test_pack_string(self):
        bigendian = self.endianess == '>'
        fmtiter = FakeFormatIter(bigendian, 'hello')
        standardfmttable.pack_string(fmtiter, 8)
        s = fmtiter.result.build()
        assert s == 'hello\x00\x00\x00'

    def test_pack_pascal(self):
        bigendian = self.endianess == '>'
        fmtiter = FakeFormatIter(bigendian, 'hello')
        standardfmttable.pack_pascal(fmtiter, 8)
        s = fmtiter.result.build()
        assert s == '\x05hello\x00\x00'


class TestPackLittleEndian(BaseTestPack):
    endianess = '<'


class TestPackBigEndian(BaseTestPack):
    endianess = '>'

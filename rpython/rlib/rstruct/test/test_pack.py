import pytest
from rpython.rlib.rstruct import standardfmttable
from rpython.rlib.mutbuffer import MutableStringBuffer
import struct

class FakeFormatIter(object):

    def __init__(self, bigendian, size, value):
        from rpython.rlib.rstring import StringBuilder
        self.value = value
        self.bigendian = bigendian
        self.result = MutableStringBuffer(size)
        # we set the buffer to non-zero, so ensure that we actively write 0s
        # where it's needed
        self.result.setslice(0, '\xff'*size)
        self.pos = 0
        self.needs_zeros = True

    def advance(self, count):
        self.pos += count

    def finish(self):
        # check that we called advance() the right number of times
        assert self.pos == self.result.getlength()
        return self.result.finish()

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
        size = struct.calcsize(fmt)
        fake_fmtiter = FakeFormatIter(bigendian, size, value)
        attrs = self.fmttable[fmt]
        pack = attrs['pack']
        pack(fake_fmtiter)
        return fake_fmtiter.finish()

    def mypack_fn(self, func, size, arg, value):
        bigendian = self.endianess == '>'
        fmtiter = FakeFormatIter(bigendian, size, value)
        func(fmtiter, arg)
        return fmtiter.finish()

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

    def test_pack_bool(self):
        self.check('?', True)
        self.check('?', False)

    def test_pack_pad(self):
        bigendian = self.endianess == '>'
        fmtiter = FakeFormatIter(bigendian, None)
        standardfmttable.pack_pad(fmtiter, 4)
        s = fmtiter.result.build()
        assert s == '\x00'*4

    def test_pack_string(self):
        s = self.mypack_fn(standardfmttable.pack_string,
                           arg=8, value='hello', size=8)
        assert s == 'hello\x00\x00\x00'
        #
        s = self.mypack_fn(standardfmttable.pack_string,
                           arg=8, value='hello world', size=8)
        assert s == 'hello wo'

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

import pytest
from rpython.rlib.rarithmetic import r_ulonglong
from rpython.rlib.rstruct import standardfmttable, nativefmttable
from rpython.rlib.mutbuffer import MutableStringBuffer
import struct

class FakeFormatIter(object):

    def __init__(self, bigendian, size, value):
        from rpython.rlib.rstring import StringBuilder
        self.value = value
        self.bigendian = bigendian
        self.result = MutableStringBuffer(size)
        self.pos = 0

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

    bigendian = None
    fmt_prefix = None
    fmttable = None

    USE_FASTPATH = True
    ALLOW_SLOWPATH = True
    
    def setup_method(self, meth):
        standardfmttable.USE_FASTPATH = self.USE_FASTPATH
        standardfmttable.ALLOW_SLOWPATH = self.ALLOW_SLOWPATH

    def teardown_method(self, meth):
        standardfmttable.USE_FASTPATH = True
        standardfmttable.ALLOW_SLOWPATH = True

    def teardown_method(self, meth):
        if not hasattr(self.fmttable, 'USE_FASTPATH'):
            return
        self.fmttable.USE_FASTPATH = self.orig_use_fastpath
        self.fmttable.ALLOW_SLOWPATH = self.orig_allow_slowpath

    def mypack(self, fmt, value):
        size = struct.calcsize(fmt)
        fake_fmtiter = FakeFormatIter(self.bigendian, size, value)
        attrs = self.fmttable[fmt]
        pack = attrs['pack']
        pack(fake_fmtiter)
        return fake_fmtiter.finish()

    def mypack_fn(self, func, size, arg, value):
        fmtiter = FakeFormatIter(self.bigendian, size, value)
        func(fmtiter, arg)
        return fmtiter.finish()

    def check(self, fmt, value):
        expected = struct.pack(self.fmt_prefix+fmt, value)
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
        self.check("Q", r_ulonglong(0x8142434445464748))

    def test_pack_ieee(self):
        self.check('f', 123.456)
        self.check('d', 123.456789)

    def test_pack_char(self):
        self.check('c', 'a')

    def test_pack_bool(self):
        self.check('?', True)
        self.check('?', False)

    def test_pack_pad(self):
        s = self.mypack_fn(standardfmttable.pack_pad,
                           arg=4, value=None, size=4)
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
        s = self.mypack_fn(standardfmttable.pack_pascal,
                           arg=8, value='hello', size=8)
        assert s == '\x05hello\x00\x00'


class TestPackLittleEndian(BaseTestPack):
    bigendian = False
    fmt_prefix = '<'
    fmttable = standardfmttable.standard_fmttable

class TestPackLittleEndianSlowPath(TestPackLittleEndian):
    USE_FASTPATH = False

class TestPackBigEndian(BaseTestPack):
    bigendian = True
    fmt_prefix = '>'
    fmttable = standardfmttable.standard_fmttable

class TestPackBigEndianSlowPath(TestPackBigEndian):
    USE_FASTPATH = False


class TestNative(BaseTestPack):
    # native packing automatically use the proper endianess, so it should
    # always take the fast path
    ALLOW_SLOWPATH = False
    bigendian = nativefmttable.native_is_bigendian
    fmt_prefix = '@'
    fmttable = nativefmttable.native_fmttable

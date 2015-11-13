from rpython.rtyper.test.tool import BaseRtypingTest
from rpython.rlib.rstruct.runpack import runpack
from rpython.rlib.rarithmetic import LONG_BIT
import struct

class TestRStruct(BaseRtypingTest):
    def test_unpack(self):
        pad = '\x00' * (LONG_BIT//8-1)    # 3 or 7 null bytes
        def fn():
            return runpack('sll', 'a'+pad+'\x03'+pad+'\x04'+pad)[1]
        assert fn() == 3
        assert self.interpret(fn, []) == 3

    def test_unpack_2(self):
        data = struct.pack('iiii', 0, 1, 2, 4)
        def fn():
            a, b, c, d = runpack('iiii', data)
            return a * 1000 + b * 100 + c * 10 + d
        assert fn() == 124
        assert self.interpret(fn, []) == 124

    def test_unpack_single(self):
        data = struct.pack('i', 123)
        def fn():
            return runpack('i', data)
        assert fn() == 123
        assert self.interpret(fn, []) == 123

    def test_unpack_big_endian(self):
        def fn():
            return runpack(">i", "\x01\x02\x03\x04")
        assert fn() == 0x01020304
        assert self.interpret(fn, []) == 0x01020304

    def test_unpack_double_big_endian(self):
        def fn():
            return runpack(">d", "testtest")
        assert fn() == struct.unpack(">d", "testtest")[0]
        assert self.interpret(fn, []) == struct.unpack(">d", "testtest")[0]

    def test_native_floats(self):
        """
        Check the 'd' and 'f' format characters on native packing.
        """
        d_data = struct.pack("d", 12.34)
        f_data = struct.pack("f", 12.34)
        def fn():
            d = runpack("@d", d_data)
            f = runpack("@f", f_data)
            return d, f
        #
        res = self.interpret(fn, [])
        d = res.item0
        f = res.item1  # convert from r_singlefloat
        assert d == 12.34     # no precision lost
        assert f != 12.34     # precision lost
        assert abs(f - 12.34) < 1E-6

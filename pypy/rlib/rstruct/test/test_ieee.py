import py, sys
import random
import struct

from pypy.rlib.rfloat import isnan
from pypy.rlib.rstruct.ieee import float_pack, float_unpack


class TestFloatPacking:

    def setup_class(cls):
        if sys.version_info < (2, 6):
            py.test.skip("the 'struct' module of this old CPython is broken")

    def check_float(self, x):
        # check roundtrip
        Q = float_pack(x, 8)
        y = float_unpack(Q, 8)
        assert repr(x) == repr(y)

        # check that packing agrees with the struct module
        struct_pack8 = struct.unpack('<Q', struct.pack('<d', x))[0]
        float_pack8 = float_pack(x, 8)
        assert struct_pack8 == float_pack8

        # check that packing agrees with the struct module
        try:
            struct_pack4 = struct.unpack('<L', struct.pack('<f', x))[0]
        except OverflowError:
            struct_pack4 = "overflow"
        try:
            float_pack4 = float_pack(x, 4)
        except OverflowError:
            float_pack4 = "overflow"
        assert struct_pack4 == float_pack4

        # if we didn't overflow, try round-tripping the binary32 value
        if float_pack4 != "overflow":
            roundtrip = float_pack(float_unpack(float_pack4, 4), 4)
            assert float_pack4 == roundtrip

    def test_infinities(self):
        self.check_float(float('inf'))
        self.check_float(float('-inf'))

    def test_zeros(self):
        self.check_float(0.0)
        self.check_float(-0.0)

    def test_nans(self):
        Q = float_pack(float('nan'), 8)
        y = float_unpack(Q, 8)
        assert repr(y) == 'nan'
        L = float_pack(float('nan'), 4)
        z = float_unpack(L, 4)
        assert repr(z) == 'nan'

    def test_simple(self):
        test_values = [1e-10, 0.00123, 0.5, 0.7, 1.0, 123.456, 1e10]
        for value in test_values:
            self.check_float(value)
            self.check_float(-value)

    def test_subnormal(self):
        # special boundaries
        self.check_float(2**-1074)
        self.check_float(2**-1022)
        self.check_float(2**-1021)
        self.check_float((2**53-1)*2**-1074)
        self.check_float((2**52-1)*2**-1074)
        self.check_float((2**52+1)*2**-1074)

        # other subnormals
        self.check_float(1e-309)
        self.check_float(1e-320)

    def test_powers_of_two(self):
        # exact powers of 2
        for k in range(-1074, 1024):
            self.check_float(2.**k)

        # and values near powers of 2
        for k in range(-1074, 1024):
            self.check_float((2 - 2**-52) * 2.**k)

    def test_float4_boundaries(self):
        # Exercise IEEE 754 binary32 boundary cases.
        self.check_float(2**128.)
        # largest representable finite binary32 value
        self.check_float((1 - 2.**-24) * 2**128.)
        # halfway case:  rounds up to an overflowing value
        self.check_float((1 - 2.**-25) * 2**128.)
        self.check_float(2**-125)
        # smallest normal
        self.check_float(2**-126)
        # smallest positive binary32 value (subnormal)
        self.check_float(2**-149)
        # 2**-150 should round down to 0
        self.check_float(2**-150)
        # but anything even a tiny bit larger should round up to 2**-149
        self.check_float((1 + 2**-52) * 2**-150)

    def test_random(self):
        # construct a Python float from random integer, using struct
        for _ in xrange(100000):
            Q = random.randrange(2**64)
            x = struct.unpack('<d', struct.pack('<Q', Q))[0]
            # nans are tricky:  we can't hope to reproduce the bit
            # pattern exactly, so check_float will fail for a random nan.
            if isnan(x):
                continue
            self.check_float(x)

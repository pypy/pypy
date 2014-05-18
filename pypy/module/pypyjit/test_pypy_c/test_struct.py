import sys
from pypy.module.pypyjit.test_pypy_c.test_00_model import BaseTestPyPyC


if sys.maxsize == 2 ** 63 - 1:
    extra = """
        i8 = int_ge(i4, -2147483648)
        guard_true(i8, descr=...)
        i9 = int_le(i4, 2147483647)
        guard_true(i9, descr=...)
    """
else:
    extra = ""


class TestStruct(BaseTestPyPyC):
    def test_struct_function(self):
        def main(n):
            import struct
            i = 1
            while i < n:
                x = struct.unpack("i", struct.pack("i", i))[0]  # ID: struct
                i += x / i
            return i

        log = self.run(main, [1000])
        assert log.result == main(1000)

        loop, = log.loops_by_filename(self.filepath)
        # This could, of course stand some improvement, to remove all these
        # arithmatic ops, but we've removed all the core overhead.
        assert loop.match_by_id("struct", """
            guard_not_invalidated(descr=...)
            # struct.pack
            %s
            i11 = int_and(i4, 255)
            i13 = int_rshift(i4, 8)
            i14 = int_and(i13, 255)
            i16 = int_rshift(i13, 8)
            i17 = int_and(i16, 255)
            i19 = int_rshift(i16, 8)
            i20 = int_and(i19, 255)

            # struct.unpack
            i22 = int_lshift(i14, 8)
            i23 = int_or(i11, i22)
            i25 = int_lshift(i17, 16)
            i26 = int_or(i23, i25)
            i28 = int_ge(i20, 128)
            guard_false(i28, descr=...)
            i30 = int_lshift(i20, 24)
            i31 = int_or(i26, i30)
        """ % extra)

    def test_struct_object(self):
        def main(n):
            import struct
            s = struct.Struct("i")
            i = 1
            while i < n:
                x = s.unpack(s.pack(i))[0]  # ID: struct
                i += x / i
            return i

        log = self.run(main, [1000])
        assert log.result == main(1000)

        loop, = log.loops_by_filename(self.filepath)
        assert loop.match_by_id('struct', """
            guard_not_invalidated(descr=...)
            # struct.pack
            %s
            i11 = int_and(i4, 255)
            i13 = int_rshift(i4, 8)
            i14 = int_and(i13, 255)
            i16 = int_rshift(i13, 8)
            i17 = int_and(i16, 255)
            i19 = int_rshift(i16, 8)
            i20 = int_and(i19, 255)

            # struct.unpack
            i22 = int_lshift(i14, 8)
            i23 = int_or(i11, i22)
            i25 = int_lshift(i17, 16)
            i26 = int_or(i23, i25)
            i28 = int_ge(i20, 128)
            guard_false(i28, descr=...)
            i30 = int_lshift(i20, 24)
            i31 = int_or(i26, i30)
        """ % extra)

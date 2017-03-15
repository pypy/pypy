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
                buf = struct.pack("<i", i)       # ID: pack
                x = struct.unpack("<i", buf)[0]  # ID: unpack
                i += x // i
            return i

        log = self.run(main, [1000])
        assert log.result == main(1000)

        loop, = log.loops_by_filename(self.filepath)
        # This could, of course stand some improvement, to remove all these
        # arithmatic ops, but we've removed all the core overhead.
        assert loop.match_by_id("pack", """
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
        """ % extra)

        if sys.byteorder == 'little':
            # the newstr and the strsetitems are because the string is forced,
            # which is in turn because the optimizer doesn't know how to handle a
            # gc_load_indexed_i on a virtual string. It could be improved, but it
            # is also true that in real life cases struct.unpack is called on
            # strings which come from the outside, so it's a minor issue.
            assert loop.match_by_id("unpack", """
                # struct.unpack
                p88 = newstr(4)
                strsetitem(p88, 0, i11)
                strsetitem(p88, 1, i14)
                strsetitem(p88, 2, i17)
                strsetitem(p88, 3, i20)
                i91 = gc_load_indexed_i(p88, 0, 1, _, -4)
            """)
        else:
            # on a big endian machine we cannot just write into
            # a char buffer and then use load gc to read the integer,
            # here manual shifting is applied
            assert loop.match_by_id("unpack", """
                # struct.unpack
                i95 = int_lshift(i90, 8)
                i96 = int_or(i88, i95)
                i97 = int_lshift(i92, 16)
                i98 = int_or(i96, i97)
                i99 = int_ge(i94, 128)
                guard_false(i99, descr=...)
                i100 = int_lshift(i94, 24)
                i101 = int_or(i98, i100)
            """)

    def test_struct_object(self):
        def main(n):
            import struct
            s = struct.Struct("ii")
            i = 1
            while i < n:
                buf = s.pack(-1, i)     # ID: pack
                x = s.unpack(buf)[1]    # ID: unpack
                i += x // i
            return i

        log = self.run(main, [1000])
        assert log.result == main(1000)

        if sys.byteorder == 'little':
            loop, = log.loops_by_filename(self.filepath)
            assert loop.match_by_id('pack', """
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
            """ % extra)

            assert loop.match_by_id('unpack', """
                # struct.unpack
                p88 = newstr(8)
                strsetitem(p88, 0, 255)
                strsetitem(p88, 1, 255)
                strsetitem(p88, 2, 255)
                strsetitem(p88, 3, 255)
                strsetitem(p88, 4, i11)
                strsetitem(p88, 5, i14)
                strsetitem(p88, 6, i17)
                strsetitem(p88, 7, i20)
                i90 = gc_load_indexed_i(p88, 0, 1, _, -4)
                i91 = gc_load_indexed_i(p88, 4, 1, _, -4)
            """)

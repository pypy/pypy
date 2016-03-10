from pypy.module.pypyjit.test_pypy_c.test_00_model import BaseTestPyPyC


class TestBuffers(BaseTestPyPyC):
    def test_re_match(self):
        def main(n):
            import re
            import array
            p = re.compile('.+')
            a = array.array('c', 'test' * 1000)
            i = 0
            while i < n:
                i += 1
                p.match(a)  # ID: match
            return i
        log = self.run(main, [1000])
        assert log.result == 1000
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match_by_id('match', """
            guard_not_invalidated(descr=...)
            i65 = getfield_gc_i(p18, descr=...)
            i67 = int_gt(0, i65)
            guard_false(i67, descr=...)
            i69 = int_gt(#, i65)
            guard_true(i69, descr=...)
            --TICK--
        """)

    def test_struct_unpack(self):
        def main(n):
            import _struct as struct
            import array
            a = array.array('c', struct.pack('i', 42))
            i = 0
            while i < n:
                i += 1
                struct.unpack('<i', a)  # ID: unpack
            return i
        log = self.run(main, [1000])
        assert log.result == 1000
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match_by_id('unpack', """
            guard_not_invalidated(descr=...)
            p90 = newstr(4)
            call_n(ConstClass(copy_raw_to_string), i55, p90, 0, 4, descr=<Callv 0 irii EF=5>)
            guard_no_exception(descr=...)
            i91 = strgetitem(p90, 0)
            i92 = strgetitem(p90, 1)
            i93 = int_lshift(i92, 8)
            i94 = int_or(i91, i93)
            i95 = strgetitem(p90, 2)
            i96 = int_lshift(i95, 16)
            i97 = int_or(i94, i96)
            i98 = strgetitem(p90, 3)
            i99 = int_ge(i98, 128)
            guard_false(i99, descr=...)
            i100 = int_lshift(i98, 24)
            i101 = int_or(i97, i100)
            i102 = getfield_raw_i(#, descr=<FieldS pypysig_long_struct.c_value 0>)
            i103 = int_lt(i102, 0)
            guard_false(i103, descr=...)
        """)

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
            i65 = getfield_gc(p18, descr=...)
            i67 = int_gt(0, i65)
            guard_false(i67, descr=...)
            i69 = int_gt(., i65)
            guard_true(i69, descr=...)
            --TICK--
        """)

    def test_struct_unpack(self):
        def main(n):
            import struct
            import array
            a = array.array('c', struct.pack('i', 42))
            i = 0
            while i < n:
                i += 1
                struct.unpack('i', a)  # ID: unpack
            return i
        log = self.run(main, [1000])
        assert log.result == 1000
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match_by_id('unpack', """
            guard_not_invalidated(descr=...)
            i93 = getarrayitem_raw(i55, 0, descr=<ArrayU 1>)
            i94 = getarrayitem_raw(i55, 1, descr=<ArrayU 1>)
            i95 = getarrayitem_raw(i55, 2, descr=<ArrayU 1>)
            i96 = getarrayitem_raw(i55, 3, descr=<ArrayU 1>)
            i97 = int_lshift(i94, 8)
            i98 = int_or(i93, i97)
            i99 = int_lshift(i95, 16)
            i100 = int_or(i98, i99)
            i101 = int_ge(i96, 128)
            guard_false(i101, descr=...)
            i102 = int_lshift(i96, 24)
            i103 = int_or(i100, i102)
            p104 = new(descr=<SizeDescr 24>)
            p105 = new_array(0, descr=<ArrayP 8>)
            setfield_gc(p104, p105, descr=<FieldP list.items 16>)
            call(ConstClass(_ll_list_resize_hint_really_look_inside_iff__listPtr_Signed_Bool), p104, 1, 1, descr=<Callv 0 rii EF=4>)
            guard_no_exception(descr=...)
            p106 = getfield_gc(p104, descr=<FieldP list.items 16>)
            i107 = getfield_raw(50657024, descr=<FieldS pypysig_long_struct.c_value 0>)
            setfield_gc(p104, 1, descr=<FieldS list.length 8>)
            i108 = int_lt(i107, 0)
            guard_false(i108, descr=...)
        """)

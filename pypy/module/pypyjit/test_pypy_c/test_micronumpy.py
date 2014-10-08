from pypy.module.pypyjit.test_pypy_c.test_00_model import BaseTestPyPyC
from rpython.rlib.rawstorage import misaligned_is_fine


class TestMicroNumPy(BaseTestPyPyC):
    def test_array_getitem_basic(self):
        def main():
            import _numpypy.multiarray as np
            arr = np.zeros((300, 300))
            x = 150
            y = 0
            while y < 300:
                a = arr[x, y]
                y += 1
            return a
        log = self.run(main, [])
        assert log.result == 0
        loop, = log.loops_by_filename(self.filepath)
        if misaligned_is_fine:
            alignment_check = ""
        else:
            alignment_check = """
                i93 = int_and(i79, 7)
                i94 = int_is_zero(i93)
                guard_true(i94, descr=...)
            """
        assert loop.match("""
            i76 = int_lt(i71, 300)
            guard_true(i76, descr=...)
            i77 = int_ge(i71, i59)
            guard_false(i77, descr=...)
            i78 = int_mul(i71, i61)
            i79 = int_add(i55, i78)
            """ + alignment_check + """
            f80 = raw_load(i67, i79, descr=<ArrayF 8>)
            i81 = int_add(i71, 1)
            guard_not_invalidated(descr=...)
            --TICK--
            jump(p0, p1, p3, p6, p7, p12, p14, p16, i81, f80, i59, p38, i55, p40, i37, i61, i67, descr=...)
        """)

    def test_array_getitem_accumulate(self):
        """Check that operations/ufuncs on array items are jitted correctly"""
        def main():
            import _numpypy.multiarray as np
            arr = np.zeros((300, 300))
            a = 0.0
            x = 150
            y = 0
            while y < 300:
                a += arr[x, y]
                y += 1
            return a
        log = self.run(main, [])
        assert log.result == 0
        loop, = log.loops_by_filename(self.filepath)
        if misaligned_is_fine:
            alignment_check = ""
        else:
            alignment_check = """
                i97 = int_and(i84, 7)
                i98 = int_is_zero(i97)
                guard_true(i98, descr=...)
            """
        assert loop.match("""
            i81 = int_lt(i76, 300)
            guard_true(i81, descr=...)
            i82 = int_ge(i76, i62)
            guard_false(i82, descr=...)
            i83 = int_mul(i76, i64)
            i84 = int_add(i58, i83)
            """ + alignment_check + """
            f85 = raw_load(i70, i84, descr=<ArrayF 8>)
            guard_not_invalidated(descr=...)
            f86 = float_add(f74, f85)
            i87 = int_add(i76, 1)
            --TICK--
            jump(p0, p1, p3, p6, p7, p12, p14, f86, p18, i87, i62, p41, i58, p47, i40, i64, i70, descr=...)
        """)

    def test_array_flatiter_getitem_single(self):
        def main():
            import _numpypy.multiarray as np
            arr = np.zeros((1024, 16)) + 42
            ai = arr.flat
            i = 0
            while i < arr.size:
                a = ai[i]
                i += 1
            return a
        log = self.run(main, [])
        assert log.result == 42.0
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i125 = int_lt(i117, i44)
            guard_true(i125, descr=...)
            i126 = int_lt(i117, i50)
            guard_true(i126, descr=...)
            i127 = int_floordiv(i117, i61)
            i128 = int_mul(i127, i61)
            i129 = int_sub(i117, i128)
            i130 = int_rshift(i129, 63)
            i131 = int_add(i127, i130)
            i132 = int_mul(i131, i71)
            i133 = int_add(i55, i132)
            i134 = int_mod(i117, i61)
            i135 = int_rshift(i134, 63)
            i136 = int_and(i61, i135)
            i137 = int_add(i134, i136)
            i138 = int_floordiv(i137, i80)
            i139 = int_mul(i138, i80)
            i140 = int_sub(i137, i139)
            i141 = int_rshift(i140, 63)
            i142 = int_add(i138, i141)
            i143 = int_mul(i142, i88)
            i144 = int_add(i133, i143)
            i145 = int_mod(i137, i80)
            i146 = int_rshift(i145, 63)
            i147 = int_and(i80, i146)
            i148 = int_add(i145, i147)
            f149 = raw_load(i100, i144, descr=<ArrayF 8>)
            p150 = getfield_gc_pure(p123, descr=<FieldP pypy.module.micronumpy.iterators.IterState.inst_indices 16>)
            i151 = int_add(i117, 1)
            setarrayitem_gc(p150, 1, 0, descr=<ArrayS 8>)
            setarrayitem_gc(p150, 0, 0, descr=<ArrayS 8>)
            guard_not_invalidated(descr=...)
            i154 = getfield_raw(ticker_address, descr=<FieldS pypysig_long_struct.c_value 0>)
            i155 = int_lt(i154, 0)
            guard_false(i155, descr=...)
            p156 = new_with_vtable(...)
            setfield_gc(p156, i55, descr=<FieldS pypy.module.micronumpy.iterators.IterState.inst_offset 32>)
            setfield_gc(p156, 0, descr=<FieldS pypy.module.micronumpy.iterators.IterState.inst_index 8>)
            setfield_gc(p156, p150, descr=<FieldP pypy.module.micronumpy.iterators.IterState.inst_indices 16>)
            setfield_gc(p156, p49, descr=<FieldP pypy.module.micronumpy.iterators.IterState.inst_iterator 24>)
            setfield_gc(p16, p156, descr=<FieldP pypy.module.micronumpy.flatiter.W_FlatIterator.inst_state 56>)
            i157 = arraylen_gc(p60, descr=<ArrayS 8>)
            i158 = arraylen_gc(p70, descr=<ArrayS 8>)
            jump(p0, p1, p3, p6, p7, p12, p14, p16, i151, f149, p26, i44, i50, i61, i71, i55, i80, i88, i100, p156, p49, p60, p70, descr=...)
        """)

    def test_array_flatiter_setitem_single(self):
        def main():
            import _numpypy.multiarray as np
            arr = np.empty((1024, 16))
            ai = arr.flat
            i = 0
            while i < arr.size:
                ai[i] = 42.0
                i += 1
            return ai[-1]
        log = self.run(main, [])
        assert log.result == 42.0
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i128 = int_lt(i120, i42)
            guard_true(i128, descr=...)
            i129 = int_lt(i120, i48)
            guard_true(i129, descr=...)
            i130 = int_floordiv(i120, i59)
            i131 = int_mul(i130, i59)
            i132 = int_sub(i120, i131)
            i133 = int_rshift(i132, 63)
            i134 = int_add(i130, i133)
            i135 = int_mul(i134, i69)
            i136 = int_add(i53, i135)
            i137 = int_mod(i120, i59)
            i138 = int_rshift(i137, 63)
            i139 = int_and(i59, i138)
            i140 = int_add(i137, i139)
            i141 = int_floordiv(i140, i78)
            i142 = int_mul(i141, i78)
            i143 = int_sub(i140, i142)
            i144 = int_rshift(i143, 63)
            i145 = int_add(i141, i144)
            i146 = int_mul(i145, i86)
            i147 = int_add(i136, i146)
            i148 = int_mod(i140, i78)
            i149 = int_rshift(i148, 63)
            i150 = int_and(i78, i149)
            i151 = int_add(i148, i150)
            guard_not_invalidated(descr=...)
            raw_store(i103, i147, 42.000000, descr=<ArrayF 8>)
            p152 = getfield_gc_pure(p126, descr=<FieldP pypy.module.micronumpy.iterators.IterState.inst_indices 16>)
            i153 = int_add(i120, 1)
            i154 = getfield_raw(ticker_address, descr=<FieldS pypysig_long_struct.c_value 0>)
            setarrayitem_gc(p152, 1, 0, descr=<ArrayS 8>)
            setarrayitem_gc(p152, 0, 0, descr=<ArrayS 8>)
            i157 = int_lt(i154, 0)
            guard_false(i157, descr=...)
            p158 = new_with_vtable(...)
            setfield_gc(p158, i53, descr=<FieldS pypy.module.micronumpy.iterators.IterState.inst_offset 32>)
            setfield_gc(p158, 0, descr=<FieldS pypy.module.micronumpy.iterators.IterState.inst_index 8>)
            setfield_gc(p158, p152, descr=<FieldP pypy.module.micronumpy.iterators.IterState.inst_indices 16>)
            setfield_gc(p158, p47, descr=<FieldP pypy.module.micronumpy.iterators.IterState.inst_iterator 24>)
            setfield_gc(p16, p158, descr=<FieldP pypy.module.micronumpy.flatiter.W_FlatIterator.inst_state 56>)
            i159 = arraylen_gc(p58, descr=<ArrayS 8>)
            i160 = arraylen_gc(p68, descr=<ArrayS 8>)
            jump(p0, p1, p3, p6, p7, p12, p14, p16, i153, i42, i48, i59, i69, i53, i78, i86, p47, i103, p158, p58, p68, descr=...)
        """)

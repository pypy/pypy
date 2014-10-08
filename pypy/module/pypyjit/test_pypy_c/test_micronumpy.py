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
            i123 = int_lt(i112, i44)
            guard_true(i123, descr=...)
            p124 = getfield_gc_pure(p121, descr=<FieldP pypy.module.micronumpy.iterators.IterState.inst_indices 16>)
            setarrayitem_gc(p124, 1, 0, descr=<ArrayS 8>)
            setarrayitem_gc(p124, 0, 0, descr=<ArrayS 8>)
            i126 = int_lt(i112, i65)
            guard_true(i126, descr=...)
            i127 = int_sub(i75, i112)
            i128 = int_lt(0, i127)
            guard_false(i128, descr=...)
            i129 = int_floordiv(i112, i75)
            i130 = int_mul(i129, i75)
            i131 = int_sub(i112, i130)
            i132 = int_rshift(i131, 63)
            i133 = int_add(i129, i132)
            i134 = int_mul(i133, i75)
            i135 = int_sub(i112, i134)
            i136 = int_mul(i91, i135)
            i137 = int_add(i64, i136)
            i138 = int_sub(i98, i133)
            setarrayitem_gc(p124, 1, i135, descr=<ArrayS 8>)
            i139 = int_lt(0, i138)
            guard_true(i139, descr=...)
            i140 = int_mul(i102, i133)
            i141 = int_add(i137, i140)
            f142 = raw_load(i108, i141, descr=<ArrayF 8>)
            i143 = int_add(i112, 1)
            setarrayitem_gc(p124, 1, 0, descr=<ArrayS 8>)
            guard_not_invalidated(descr=...)
            i144 = getfield_raw(ticker_address, descr=<FieldS pypysig_long_struct.c_value 0>)
            i145 = int_lt(i144, 0)
            guard_false(i145, descr=...)
            p146 = new_with_vtable(...)
            setfield_gc(p146, p49, descr=<FieldP pypy.module.micronumpy.iterators.IterState.inst_iterator 24>)
            setfield_gc(p146, p124, descr=<FieldP pypy.module.micronumpy.iterators.IterState.inst_indices 16>)
            setfield_gc(p146, i64, descr=<FieldS pypy.module.micronumpy.iterators.IterState.inst_offset 32>)
            setfield_gc(p146, 0, descr=<FieldS pypy.module.micronumpy.iterators.IterState.inst_index 8>)
            setfield_gc(p16, p146, descr=<FieldP pypy.module.micronumpy.flatiter.W_FlatIterator.inst_state 56>)
            i147 = arraylen_gc(p72, descr=<ArrayS 8>)
            i148 = arraylen_gc(p90, descr=<ArrayS 8>)
            jump(p0, p1, p3, p6, p7, p12, p14, p16, i143, f142, p26, i44, p146, i65, p49, i64, i75, i91, i98, i102, i108, p72, p90, descr=...)
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
            i126 = int_lt(i115, i42)
            guard_true(i126, descr=...)
            i127 = int_lt(i115, i48)
            guard_true(i127, descr=...)
            p128 = getfield_gc_pure(p124, descr=<FieldP pypy.module.micronumpy.iterators.IterState.inst_indices 16>)
            i129 = int_sub(i73, i115)
            setarrayitem_gc(p128, 1, 0, descr=<ArrayS 8>)
            setarrayitem_gc(p128, 0, 0, descr=<ArrayS 8>)
            i131 = int_lt(0, i129)
            guard_false(i131, descr=...)
            i132 = int_floordiv(i115, i73)
            i133 = int_mul(i132, i73)
            i134 = int_sub(i115, i133)
            i135 = int_rshift(i134, 63)
            i136 = int_add(i132, i135)
            i137 = int_mul(i136, i73)
            i138 = int_sub(i115, i137)
            i139 = int_mul(i89, i138)
            i140 = int_add(i66, i139)
            i141 = int_sub(i96, i136)
            setarrayitem_gc(p128, 1, i138, descr=<ArrayS 8>)
            i142 = int_lt(0, i141)
            guard_true(i142, descr=...)
            i143 = int_mul(i100, i136)
            i144 = int_add(i140, i143)
            setarrayitem_gc(p128, 0, i136, descr=<ArrayS 8>)
            guard_not_invalidated(descr=...)
            raw_store(i111, i144, 42.000000, descr=<ArrayF 8>)
            i146 = int_add(i115, 1)
            i147 = getfield_raw(ticker_address, descr=<FieldS pypysig_long_struct.c_value 0>)
            setarrayitem_gc(p128, 1, 0, descr=<ArrayS 8>)
            setarrayitem_gc(p128, 0, 0, descr=<ArrayS 8>)
            i149 = int_lt(i147, 0)
            guard_false(i149, descr=...)
            p150 = new_with_vtable(...)
            setfield_gc(p150, p47, descr=<FieldP pypy.module.micronumpy.iterators.IterState.inst_iterator 24>)
            setfield_gc(p150, p128, descr=<FieldP pypy.module.micronumpy.iterators.IterState.inst_indices 16>)
            setfield_gc(p150, i66, descr=<FieldS pypy.module.micronumpy.iterators.IterState.inst_offset 32>)
            setfield_gc(p150, 0, descr=<FieldS pypy.module.micronumpy.iterators.IterState.inst_index 8>)
            setfield_gc(p16, p150, descr=<FieldP pypy.module.micronumpy.flatiter.W_FlatIterator.inst_state 56>)
            i151 = arraylen_gc(p70, descr=<ArrayS 8>)
            i152 = arraylen_gc(p88, descr=<ArrayS 8>)
            jump(p0, p1, p3, p6, p7, p12, p14, p16, i146, i42, i48, p150, i73, i66, p47, i89, i96, i100, i111, p70, p88, descr=...)
        """)

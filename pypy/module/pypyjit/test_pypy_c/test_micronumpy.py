from pypy.module.pypyjit.test_pypy_c.test_00_model import BaseTestPyPyC


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
        assert loop.match("""
            i76 = int_lt(i71, 300)
            guard_true(i76, descr=...)
            i77 = int_ge(i71, i59)
            guard_false(i77, descr=...)
            i78 = int_mul(i71, i61)
            i79 = int_add(i55, i78)
            f80 = raw_load(i67, i79, descr=<ArrayF 8>)
            i81 = int_add(i71, 1)
            guard_not_invalidated(descr=...)
            --TICK--
            jump(p0, p1, p3, p6, p7, p12, p14, p16, i81, f80, i59, p38, i55, p40, i37, i61, i67, descr=...)
        """)

    def test_array_getitem_accumulate(self):
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
        skip('used to pass on 69421-f3e717c94913')
        assert loop.match("""
            i81 = int_lt(i76, 300)
            guard_true(i81, descr=...)
            i82 = int_ge(i76, i62)
            guard_false(i82, descr=...)
            i83 = int_mul(i76, i64)
            i84 = int_add(i58, i83)
            f85 = raw_load(i70, i84, descr=<ArrayF 8>)
            guard_not_invalidated(descr=...)
            f86 = float_add(f74, f85)
            i87 = int_add(i76, 1)
            --TICK--
            jump(p0, p1, p3, p6, p7, p12, p14, f86, p18, i87, i62, p41, i58, p47, i40, i64, i70, descr=...)
        """)

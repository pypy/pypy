from pypy.module.pypyjit.test_pypy_c.test_00_model import BaseTestPyPyC


class TestMath(BaseTestPyPyC):
    def test_log(self):
        def main(n):
            import math

            i = 1
            s = 0.0
            while i < n:
                s += math.log(i) - math.log10(i)
                i += 1
            return s
        log = self.run(main, [500])
        assert round(log.result, 6) == round(main(500), 6)
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i2 = int_lt(i0, i1)
            guard_true(i2, descr=...)
            guard_not_invalidated(descr=...)
            f1 = cast_int_to_float(i0)
            i3 = float_le(f1, 0)
            guard_false(i3, descr=...)
            f2 = call(ConstClass(log), f1, descr=<FloatCallDescr>)
            f3 = call(ConstClass(log10), f1, descr=<FloatCallDescr>)
            f4 = float_sub(f2, f3)
            f5 = float_add(f0, f4)
            i4 = int_add(i0, 1)
            --TICK--
            jump(..., descr=<Loop0>)
        """)

    def test_sin_cos(self):
        def main(n):
            import math

            i = 1
            s = 0.0
            while i < n:
                s += math.sin(i) - math.cos(i)
                i += 1
            return s
        log = self.run(main, [500])
        assert round(log.result, 6) == round(main(500), 6)
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i2 = int_lt(i0, i1)
            guard_true(i2, descr=...)
            guard_not_invalidated(descr=...)
            f1 = cast_int_to_float(i0)
            i3 = float_eq(f1, inf)
            i4 = float_eq(f1, -inf)
            i5 = int_or(i3, i4)
            i6 = int_is_true(i5)
            guard_false(i6, descr=...)
            f2 = call(ConstClass(sin), f1, descr=<FloatCallDescr>)
            f3 = call(ConstClass(cos), f1, descr=<FloatCallDescr>)
            f4 = float_sub(f2, f3)
            f5 = float_add(f0, f4)
            i7 = int_add(i0, f1)
            --TICK--
            jump(..., descr=)
        """)

    def test_fmod(self):
        def main(n):
            import math

            s = 0
            while n > 0:
                s += math.fmod(n, 2.0)
                n -= 1
            return s
        log = self.run(main, [500])
        assert log.result == main(500)
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i1 = int_gt(i0, 0)
            guard_true(i1, descr=...)
            f1 = cast_int_to_float(i0)
            i2 = float_eq(f1, inf)
            i3 = float_eq(f1, -inf)
            i4 = int_or(i2, i3)
            i5 = int_is_true(i4)
            guard_false(i5, descr=...)
            f2 = call(ConstClass(fmod), f1, 2.0, descr=<FloatCallDescr>)
            f3 = float_add(f0, f2)
            i6 = int_sub(i0, 1)
            --TICK--
            jump(..., descr=)
        """)
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
            f2 = call(ConstClass(log), f1)
            f3 = call(ConstClass(log10), f1)
            f4 = float_sub(f2, f3)
            f5 = float_add(f0, f4)
            i4 = int_add(i0, 1)
            --TICK--
            jump(i4, i1, f5)
        """)

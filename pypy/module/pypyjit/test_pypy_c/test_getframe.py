from pypy.module.pypyjit.test_pypy_c.test_00_model import BaseTestPyPyC


class TestGetFrame(BaseTestPyPyC):
    def test_getframe_one(self):
        def main(n):
            import sys

            i = 0
            while i < n:
                assert sys._getframe(0).f_code.co_filename == __file__
                i += 1
            return i

        log = self.run(main, [300])
        assert log.result == 300
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
        i54 = int_lt(i47, i28)
        guard_true(i54, descr=...)
        guard_not_invalidated(descr=...)
        i55 = int_add(i47, 1)
        --TICK--
        jump(..., descr=...)
        """)

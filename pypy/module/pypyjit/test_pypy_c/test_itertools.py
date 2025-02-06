import pytest, sys
from pypy.module.pypyjit.test_pypy_c.test_00_model import BaseTestPyPyC


class TestMisc(BaseTestPyPyC):
    def test_islice_step_is_1(self):
        def f1(n):
            import itertools
            l = [1] * 10000
            res = 0
            for x in itertools.islice(l, n):
                res += x
            return res
        log = self.run(f1, [2117])
        assert log.result == 2117
        loop, = log.loops_by_filename(self.filepath)
        opnames = log.opnames(loop.allops())
        assert not any("call" in name for name in opnames)


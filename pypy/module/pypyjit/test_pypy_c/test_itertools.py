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

    def test_islice_uses_greenkey(self):
        def f1(n):
            def f(a):
                return a + 1
            def g(a):
                return a + 2
            import itertools
            l = [1] * 10000
            res = 0
            for x in itertools.islice(map(f, l), 0, n, 2000):
                res += x
            for x in itertools.islice(map(g, l), 0, n, 2000):
                res += x
            return res
        log = self.run(f1, [2117])
        # must be two different islice_ignore_items loops, and not a bridge
        loop0, loop1 = [loop for loop in log.loops if 'islice_ignore_items' in str(loop)]
        assert not any(getattr(op, 'bridge', None) is not None for op in loop0.allops())

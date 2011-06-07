import py
from pypy.module.pypyjit.test_pypy_c.test_model import BaseTestPyPyC

class TestMinMax(BaseTestPyPyC):

    def test_min_max(self):
        def main():
            i=0
            sa=0
            while i < 300:
                sa+=min(max(i, 3000), 4000)
                i+=1
            return sa
        log = self.run(main, [])
        assert log.result == 300*3000
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i7 = int_lt(i4, 300)
            guard_true(i7, descr=...)
            i9 = int_add_ovf(i5, 3000)
            guard_no_overflow(descr=...)
            i11 = int_add(i4, 1)
            --TICK--
            jump(p0, p1, p2, p3, i11, i9, descr=<Loop0>)
        """)

    def test_silly_max(self):
        def main():
            i = 2
            sa = 0
            while i < 300:
                lst = range(i)
                sa += max(*lst) # ID: max
                i += 1
            return sa
        log = self.run(main, [])
        assert log.result == main()
        loop, = log.loops_by_filename(self.filepath)
        # We dont want too many guards, but a residual call to min_max_loop
        guards = [n for n in log.opnames(loop.ops_by_id("max")) if n.startswith('guard')]
        assert len(guards) < 20
        assert loop.match_by_id('max',"""
            ...
            p76 = call_may_force(ConstClass(min_max_loop__max), _, _, descr=...)
            ...
        """)

    def test_iter_max(self):
        def main():
            i = 2
            sa = 0
            while i < 300:
                lst = range(i)
                sa += max(lst) # ID: max
                i += 1
            return sa
        log = self.run(main, [])
        assert log.result == main()
        loop, = log.loops_by_filename(self.filepath)
        # We dont want too many guards, but a residual call to min_max_loop
        guards = [n for n in log.opnames(loop.ops_by_id("max")) if n.startswith('guard')]
        assert len(guards) < 20
        assert loop.match_by_id('max',"""
            ...
            p76 = call_may_force(ConstClass(min_max_loop__max), _, _, descr=...)
            ...
        """)

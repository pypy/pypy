import py
from pypy.module.pypyjit.test_pypy_c.test_00_model import BaseTestPyPyC

class TestCProfile(BaseTestPyPyC):

    def test_cprofile_builtin(self):
        def main(n):
            import _lsprof
            prof = _lsprof.Profiler()
            i = 0
            lst = []
            prof.enable()
            while i < n:
                lst.append(i)   # ID: append
                lst.pop()       # ID: pop
                i += 1
            prof.disable()
            return [(entry.code, entry.callcount) for entry in prof.getstats()]
        #
        log = self.run(main, [500])
        assert sorted(log.result) == [
            ("<method 'append' of 'list' objects>", 500),
            ("<method 'disable' of '_lsprof.Profiler' objects>", 1),
            ("<method 'pop' of 'list' objects>", 500),
            ]
        for method in ['append', 'pop']:
            loop, = log.loops_by_id(method)
            print loop.ops_by_id(method)
            assert ' call(' not in repr(loop.ops_by_id(method))
            assert ' call_may_force(' not in repr(loop.ops_by_id(method))
            assert ' cond_call(' in repr(loop.ops_by_id(method))

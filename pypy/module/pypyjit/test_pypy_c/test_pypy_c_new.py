import py, sys, re
import subprocess
from lib_pypy import disassembler
from pypy.tool.udir import udir
from pypy.tool import logparser
from pypy.module.pypyjit.test_pypy_c.model import Log
from pypy.module.pypyjit.test_pypy_c.test_model import BaseTestPyPyC


class TestPyPyCNew(BaseTestPyPyC):
    def test_f1(self):
        def f1(n):
            "Arbitrary test function."
            i = 0
            x = 1
            while i<n:
                j = 0
                while j<=i:
                    j = j + 1
                    x = x + (i&j)
                i = i + 1
            return x
        log = self.run(f1, [2117])
        assert log.result == 1083876708
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i9 = int_le(i7, i8)
            guard_true(i9)
            i11 = int_add_ovf(i7, 1)
            guard_no_overflow()
            i12 = int_and(i8, i11)
            i13 = int_add_ovf(i6, i12)
            guard_no_overflow()
            --TICK--
            jump(p0, p1, p2, p3, p4, p5, i13, i11, i8)
        """)

    def test_cmp_exc(self):
        def f1(n):
            def f():
                raise KeyError

            i = 0
            while i < n:
                try:
                    f()
                except KeyError: # ID: except
                    i += 1
            return i

        log = self.run(f1, [10000])
        assert log.result == 10000
        loop, = log.loops_by_id("except")
        ops = [o.name for o in loop.ops_by_id("except")]
        assert "call_may_force" not in ops
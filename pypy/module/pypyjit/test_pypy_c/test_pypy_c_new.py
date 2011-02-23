import py, sys, re
import subprocess
from lib_pypy import disassembler
from pypy.tool.udir import udir
from pypy.tool import logparser
from pypy.module.pypyjit.test_pypy_c.model import Log
from pypy.module.pypyjit.test_pypy_c.test_model import BaseTestPyPyC


class TestInfrastructure(BaseTestPyPyC):

    def test_full(self):
        py.test.skip('in-progress')
        def f():
            i = 0
            while i < 1003:
                # LOOP one
                i += 1

        trace = self.run(f)
        loop = trace.get_loops('one')
        loop.get_bytecode(3, 'LOAD_FAST').match('''
        int_add
        guard_true
        ''')
        loop.get_bytecode(4, 'LOAD_CONST').match_stats(
            guard='3', call='1-2', call_may_force='0'
        )
        # this would make operations that are "costly" obligatory to pass
        # like new
        loo.get_bytecode(5, 'INPLACE_ADD').match_stats(
            allocs='5-10'
            )

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
            i16 = getfield_raw(37212896)
            i18 = int_sub(i16, 1)
            setfield_raw(37212896, i18)
            i20 = int_lt(i18, 0)
            guard_false(i20)
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
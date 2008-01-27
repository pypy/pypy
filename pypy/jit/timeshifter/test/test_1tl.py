from pypy.rpython.module.support import LLSupport
from pypy.jit.timeshifter.test.test_timeshift import TimeshiftingTests
from pypy.jit.timeshifter.test.test_vlist import P_OOPSPEC
from pypy.tool.sourcetools import func_with_new_name
from pypy.jit.conftest import Benchmark

from pypy.jit.tl import tl
from pypy.jit.tl.test.test_tl import FACTORIAL_SOURCE


class TestTL(TimeshiftingTests):

    def test_tl(self):
        code = tl.compile(FACTORIAL_SOURCE)
        bytecode = ','.join([str(ord(c)) for c in code])
        tl_interp_without_call = func_with_new_name(
            tl.interp_without_call, "tl_interp_without_call")
        # to stick attributes on the new function object, not on tl.interp_wit*
        def build_bytecode(s):
            result = ''.join([chr(int(t)) for t in s.split(',')])
            return LLSupport.to_rstr(result)
        tl_interp_without_call.convert_arguments = [build_bytecode, int, int]

        if Benchmark.ENABLED:
            n = 2500
            expected = 0      # far too many powers of 2 to be anything else
        else:
            n = 5
            expected = 120
        res = self.timeshift(tl_interp_without_call, [bytecode, 0, n],
                             [0, 1], policy=P_OOPSPEC)
        assert res == expected

from pypy.rpython.lltypesystem.rstr import string_repr
from pypy.jit.timeshifter.test.test_timeshift import TimeshiftingTests
from pypy.jit.timeshifter.test.test_vlist import P_OOPSPEC

from pypy.jit.tl import tl
from pypy.jit.tl.test.test_tl import FACTORIAL_SOURCE


class TestTL(TimeshiftingTests):

    def test_tl(self):
        import py; py.test.skip("in-progress")
        code = tl.compile(FACTORIAL_SOURCE)
        ll_code = string_repr.convert_const(code)
        insns, res = self.timeshift(tl.interp_without_call,
                                    [ll_code, 0, 5], [0, 1],
                                    policy=P_OOPSPEC)
        assert res == 120

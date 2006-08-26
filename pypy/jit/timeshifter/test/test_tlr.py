from pypy.rpython.lltypesystem.rstr import string_repr
from pypy.jit.timeshifter.test.test_timeshift import TimeshiftingTests
from pypy.jit.timeshifter.test.test_vlist import P_OOPSPEC

from pypy.jit.tl import tlr


class TestTLR(TimeshiftingTests):

    def test_tlr(self):
        bytecode = string_repr.convert_const(tlr.SQUARE)
        res = self.timeshift(tlr.interpret, [bytecode, 9], [0],
                             policy=P_OOPSPEC)
        assert res == 81

from pypy.rpython.module.support import LLSupport
from pypy.jit.timeshifter.test.test_portal import PortalTest
from pypy.jit.timeshifter.test.test_vlist import P_OOPSPEC
from pypy.tool.sourcetools import func_with_new_name

from pypy.jit.tl import tlr


class TestTLR(PortalTest):

    def test_tlr(self):
        bytecode = ','.join([str(ord(c)) for c in tlr.SQUARE])
        tlr_interpret = func_with_new_name(tlr.interpret, "tlr_interpret")
        # to stick attributes on the new function object, not on tlr.interpret
        def build_bytecode(s):
            result = ''.join([chr(int(t)) for t in s.split(',')])
            return LLSupport.to_rstr(result)
        tlr_interpret.convert_arguments = [build_bytecode, int]

        res = self.timeshift_from_portal(tlr_interpret, tlr_interpret, [bytecode, 1764],
                             policy=P_OOPSPEC)
        assert res == 3111696

        res = self.timeshift_from_portal(tlr_interpret, tlr_interpret, [bytecode, 9],
                             policy=P_OOPSPEC)
        assert res == 81

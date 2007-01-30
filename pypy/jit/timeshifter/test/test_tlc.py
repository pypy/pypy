import py
from pypy.rpython.module.support import LLSupport
from pypy.jit.timeshifter.test.test_portal import PortalTest
from pypy.jit.timeshifter.test.test_vlist import P_OOPSPEC
from pypy.tool.sourcetools import func_with_new_name
from pypy.jit.conftest import Benchmark

from pypy.jit.tl import tlc
from pypy.jit.tl.test.test_tl import FACTORIAL_SOURCE


tlc_interp_without_call = func_with_new_name(
    tlc.interp_without_call, "tlc_interp_without_call")
tlc_interp_eval_without_call = tlc.interp_eval_without_call

# to stick attributes on the new function object, not on tlc.interp_wi*
def build_bytecode(s):
    result = ''.join([chr(int(t)) for t in s.split(',')])
    return LLSupport.to_rstr(result)
tlc_interp_without_call.convert_arguments = [build_bytecode, int, int]


class TestTLC(PortalTest):
    small = False

    def test_factorial(self):
        code = tlc.compile(FACTORIAL_SOURCE)
        bytecode = ','.join([str(ord(c)) for c in code])

        n = 5
        expected = 120

        res = self.timeshift_from_portal(tlc_interp_without_call,
                                         tlc_interp_eval_without_call,
                                         [bytecode, 0, n],
                                         policy=P_OOPSPEC)#, backendoptimize=True)
        assert res == expected
        self.check_insns(malloc=1)

    def test_nth_item(self):
        # get the nth item of a chained list
        code = tlc.compile("""
            NIL
            PUSH 40
            CONS
            PUSH 20
            CONS
            PUSH 10
            CONS
            PUSHARG
            DIV
        """)
        bytecode = ','.join([str(ord(c)) for c in code])
        res = self.timeshift_from_portal(tlc_interp_without_call,
                                         tlc_interp_eval_without_call,
                                         [bytecode, 0, 1],
                                         policy=P_OOPSPEC)#, backendoptimize=True)
        assert res == 20

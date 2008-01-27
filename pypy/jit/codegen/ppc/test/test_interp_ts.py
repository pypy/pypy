from pypy.jit.codegen.ppc.conftest import option
import py
from pypy.jit.codegen.i386.test.test_interp_ts import I386LLInterpTimeshiftingTestMixin
from pypy.jit.timeshifter.test import test_timeshift

def setup_module(mod):
    if not option.run_interp_tests:
        py.test.skip("these tests take ages and are not really useful")


class PPCLLInterpTimeshiftingTestMixin(I386LLInterpTimeshiftingTestMixin):
    from pypy.jit.codegen.ppc.test.test_interp import LLTypeRGenOp as RGenOp

class TestTimeshiftPPC(PPCLLInterpTimeshiftingTestMixin,
                       test_timeshift.TestLLType):

    # for the individual tests see
    # ====> ../../../timeshifter/test/test_timeshift.py

    pass


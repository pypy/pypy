import py
from pypy.jit.codegen.i386.test.test_genc_ts import I386TimeshiftingTestMixin
from pypy.jit.timeshifter.test import test_timeshift
from pypy.jit.codegen.ppc.rgenop import RPPCGenOp

class PPCTimeshiftingTestMixin(I386TimeshiftingTestMixin):
    RGenOp = RPPCGenOp

class TestTimeshiftPPC(PPCTimeshiftingTestMixin,
                        test_timeshift.TestLLType):

    # for the individual tests see
    # ====> ../../../timeshifter/test/test_timeshift.py

    pass


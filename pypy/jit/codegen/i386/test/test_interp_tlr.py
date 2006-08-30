import py
from pypy.jit.timeshifter.test import test_tlr
from pypy.jit.codegen.i386.test.test_interp_ts import I386LLInterpTimeshiftingTestMixin


class TestTLR(I386LLInterpTimeshiftingTestMixin,
              test_tlr.TestTLR):

    # for the individual tests see
    # ====> ../../../timeshifter/test/test_tlr.py

    pass

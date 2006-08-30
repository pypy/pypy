import py
from pypy.jit.timeshifter.test import test_tlr
from pypy.jit.codegen.i386.test.test_genc_ts import I386TimeshiftingTestMixin


class TestTLR(I386TimeshiftingTestMixin,
              test_tlr.TestTLR):

    # for the individual tests see
    # ====> ../../../timeshifter/test/test_tlr.py

    pass

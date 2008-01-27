import py
from pypy.jit.timeshifter.test import test_tlr
from pypy.jit.codegen.llvm.test.test_genc_ts import LLVMTimeshiftingTestMixin


py.test.skip("WIP")

class TestTLR(LLVMTimeshiftingTestMixin,
              test_tlr.TestTLR):

    # for the individual tests see
    # ====> ../../../timeshifter/test/test_tlr.py

    pass

import py
from pypy.jit.timeshifter.test import test_tl
from pypy.jit.codegen.llvm.test.test_genc_ts import LLVMTimeshiftingTestMixin


py.test.skip("WIP")

class TestTL(LLVMTimeshiftingTestMixin,
              test_tl.TestTL):

    # for the individual tests see
    # ====> ../../../timeshifter/test/test_tl.py

    pass

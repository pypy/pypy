import py
from pypy.jit.timeshifter.test import test_vlist
from pypy.jit.codegen.llvm.test.test_genc_ts import LLVMTimeshiftingTestMixin


class TestVList(LLVMTimeshiftingTestMixin,
                test_vlist.TestVList):

    # for the individual tests see
    # ====> ../../../timeshifter/test/test_vlist.py

    pass

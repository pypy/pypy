import py
from pypy.jit.timeshifter.test import test_exception
from pypy.jit.codegen.llvm.test.test_genc_ts import LLVMTimeshiftingTestMixin


class TestException(LLVMTimeshiftingTestMixin,
                    test_exception.TestException):

    # for the individual tests see
    # ====> ../../../timeshifter/test/test_exception.py

    pass

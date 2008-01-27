import py
from pypy.jit.timeshifter.test import test_exception
from pypy.jit.codegen.llvm.test.test_genc_ts import LLVMTimeshiftingTestMixin
from pypy.jit.codegen.llvm.llvmjit import llvm_version, MINIMAL_VERSION


class TestException(LLVMTimeshiftingTestMixin,
                    test_exception.TestException):

    # for the individual tests see
    # ====> ../../../timeshifter/test/test_exception.py

    def skip_too_minimal(self):
        py.test.skip('found llvm %.1f, requires at least llvm %.1f(cvs)' % (
            llvm_version(), MINIMAL_VERSION))

    if llvm_version() < 2.0:
        test_catch = skip_too_minimal

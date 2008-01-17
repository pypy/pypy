import py
from pypy.jit.codegen.i386.test.test_genc_ts import I386TimeshiftingTestMixin
from pypy.jit.timeshifter.test import test_timeshift
from pypy.jit.codegen.llvm.rgenop import RLLVMGenOp
from pypy.jit.codegen.llvm.llvmjit import llvm_version, MINIMAL_VERSION


class LLVMTimeshiftingTestMixin(I386TimeshiftingTestMixin):
    RGenOp = RLLVMGenOp


class TestTimeshiftLLVM(LLVMTimeshiftingTestMixin,
                        test_timeshift.TestLLType):

    # for the individual tests see
    # ====> ../../../timeshifter/test/test_timeshift.py

    def skip(self):
        py.test.skip("WIP")

    def skip_too_minimal(self):
        py.test.skip('found llvm %.1f, requires at least llvm %.1f(cvs)' % (
            llvm_version(), MINIMAL_VERSION))

    if llvm_version() < 2.0:
        test_loop_merging = skip_too_minimal #segfault
        test_two_loops_merging = skip_too_minimal #segfault
        test_green_char_at_merge = skip #segfault
        test_residual_red_call_with_exc = skip

    def test_simple_red_meth(self):
        py.test.skip('no frame var support yet')

    test_simple_red_meth_vars_around = test_simple_red_meth


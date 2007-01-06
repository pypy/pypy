import py
from pypy.jit.codegen.llvm.test.test_llvmjit import skip_unsupported_platform
from pypy.jit.codegen.i386.test.test_operation import BasicTests
from pypy.jit.codegen.llvm.rgenop import RLLVMGenOp
from pypy.jit.codegen.llvm.llvmjit import llvm_version, MINIMAL_VERSION


class LLVMTestBasicMixin(object):
    RGenOp = RLLVMGenOp


class TestBasic(LLVMTestBasicMixin,
                BasicTests):

    # for the individual tests see
    # ====> ../../i386/test/test_operation.py

    def skip(self):
        py.test.skip('WIP')

    def skip_too_minimal(self):
        py.test.skip('found llvm %.1f, requires at least llvm %.1f(cvs)' % (
            llvm_version(), MINIMAL_VERSION))

    if llvm_version() < 2.0:
        test_float_arithmetic = skip_too_minimal #segfault
        test_unsigned = skip_too_minimal #uint_invert uses incorrect xor constant?

    test_float_pow = skip
    test_unichar_array = skip
    test_char_unichar_fields = skip

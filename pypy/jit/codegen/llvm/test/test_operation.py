import py
from pypy.rlib.objectmodel import specialize
from pypy.rpython.memory.lltypelayout import convert_offset_to_int
from pypy.jit.codegen.llvm.test.test_llvmjit import skip_unsupported_platform
from pypy.jit.codegen.test.operation_tests import OperationTests
from pypy.jit.codegen.llvm.rgenop import RLLVMGenOp
from pypy.jit.codegen.llvm.llvmjit import llvm_version, MINIMAL_VERSION


def conv(n):
    if not isinstance(n, int) and not isinstance(n, str):
        n = convert_offset_to_int(n)
    return n


class RGenOpPacked(RLLVMGenOp):
    """Like RLLVMGenOp, but produces concrete offsets in the tokens
    instead of llmemory.offsets.  These numbers may not agree with
    your C compiler's.
    """

    @staticmethod
    @specialize.memo()
    def fieldToken(T, name):
        return tuple(map(conv, RLLVMGenOp.fieldToken(T, name)))

    @staticmethod
    @specialize.memo()
    def arrayToken(A):
        return tuple(map(conv, RLLVMGenOp.arrayToken(A)))

    @staticmethod
    @specialize.memo()
    def allocToken(T):
        return conv(RLLVMGenOp.allocToken(T))

    @staticmethod
    @specialize.memo()
    def varsizeAllocToken(A):
        return tuple(map(conv, RLLVMGenOp.varsizeAllocToken(A)))


class LLVMTestBasicMixin(object):
    RGenOp = RGenOpPacked


class TestBasic(LLVMTestBasicMixin,
                OperationTests):

    # for the individual tests see
    # ====> ../../test/operation_tests.py

    def skip(self):
        py.test.skip('WIP')

    def skip_too_minimal(self):
        py.test.skip('found llvm %.1f, requires at least llvm %.1f(cvs)' % (
            llvm_version(), MINIMAL_VERSION))

    if llvm_version() < 2.0:
        test_unsigned = skip_too_minimal #uint_invert uses incorrect xor constant?
        test_unsigned_comparison = skip_too_minimal

    test_unsigned = skip #?
    test_arithmetic = skip #XXX << 32 and >> 32 fail 

    test_constants_in_divmod = skip #in-progress

    test_float_arithmetic = skip #XXX llvmjit.execute() returns an int :-(
    test_float_cast = skip       #XXX llvmjit.execute() returns an int :-(

    test_unichar_array = skip
    test_char_unichar_fields = skip

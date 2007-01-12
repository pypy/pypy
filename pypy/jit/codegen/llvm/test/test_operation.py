import py
from pypy.rlib.objectmodel import specialize
from pypy.rpython.memory.lltypelayout import convert_offset_to_int
from pypy.jit.codegen.llvm.test.test_llvmjit import skip_unsupported_platform
from pypy.jit.codegen.i386.test.test_operation import BasicTests
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
                BasicTests):

    # for the individual tests see
    # ====> ../../i386/test/test_operation.py

    def skip(self):
        py.test.skip('WIP')

    def skip_too_minimal(self):
        py.test.skip('found llvm %.1f, requires at least llvm %.1f(cvs)' % (
            llvm_version(), MINIMAL_VERSION))

    if llvm_version() < 2.0:
        test_float_arithmetic = skip_too_minimal #40.0 + 2.0 = 2.0? (mmx issue?)
        test_unsigned = skip_too_minimal #uint_invert uses incorrect xor constant?

    test_float_cast = skip #works when f64 is 'float' but not when 'double' because of 0.0 compare
    test_float_pow = skip
    test_unichar_array = skip
    test_char_unichar_fields = skip

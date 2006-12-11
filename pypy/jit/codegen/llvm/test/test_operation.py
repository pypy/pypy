import py
from pypy.jit.codegen.llvm.test.test_llvmjit import skip_unsupported_platform
from pypy.jit.codegen.i386.test.test_operation import BasicTests
from pypy.jit.codegen.llvm.rgenop import RLLVMGenOp


skip_unsupported_platform()
#py.test.skip('WIP')

class LLVMTestBasicMixin(object):
    RGenOp = RLLVMGenOp

class TestBasic(LLVMTestBasicMixin,
                BasicTests):

    # for the individual tests see
    # ====> ../../../i386/test/test_operation.py

    def skip(self):
        py.test.skip('WIP')

    test_comparison = skip
    test_char_comparison = skip
    test_unichar_comparison = skip
    test_char_array = skip
    test_char_varsize_array = skip
    test_unichar_array = skip
    test_char_unichar_fields = skip
    test_unsigned = skip


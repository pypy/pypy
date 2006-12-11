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
    # ====> ../../i386/test/test_operation.py

    def skip(self):
        py.test.skip('WIP')

    test_unsigned = skip
    #XXX -r_uint(n) generated op_int_sub(0,n) , why not op_uint_sub?

    test_float_arithmetic = skip
    #XXX bool(f - 2.0) generated op_float_sub(f,IntConst(2)) , why not FloatConst(2.0) ?
    #   E           assert fp(40.0, 2.0) == fn(40.0, 2.0)
    #   >           ArgumentError: argument 1: exceptions.TypeError: int expected instead of float instance

    #   [/mnt/hdb3/projects.eric/pypy-dist/pypy/jit/codegen/i386/test/test_operation.py:240]

    test_char_array = skip
    test_char_varsize_array = skip
    test_unichar_array = skip
    test_char_unichar_fields = skip


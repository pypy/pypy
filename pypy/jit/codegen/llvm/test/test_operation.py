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

    #test_unsigned = skip
    #XXX -r_uint(n) generated op_int_sub(0,n) , why not op_uint_sub?
    # -AR- for me it crashes on the 'x%y' test.  The LLVM ref manual
    #      seems to mention only 'srem' and 'urem' instructions and
    #      not 'rem'.  Same for 'sdiv' and 'udiv' and no 'div'.
    #      Strange, the translator/llvm backend seems to produce
    #      'div' and 'rem' anyway...
    # -ER- the langref on llvm.org seems to be for the upcoming llvm version 2.0
    # -AR- I see in llvm.rgenop that op_uint_invert uses an IntConst
    #      (should be UIntConst).
    # -ER- indeed

    test_float_arithmetic = skip
    #XXX bool(f - 2.0) generated op_float_sub(f,IntConst(2)) , why not FloatConst(2.0) ?
    #   E           assert fp(40.0, 2.0) == fn(40.0, 2.0)
    #   >           ArgumentError: argument 1: exceptions.TypeError: int expected instead of float instance

    #   [/mnt/hdb3/projects.eric/pypy-dist/pypy/jit/codegen/i386/test/test_operation.py:240]
    # -AR- the ctypes function type need to be fixed in rgen() in
    #      i386.test.test_operation.  For now it assumes that all args are
    #      c_int.  The llvm.rgenop.genconst() method should have more cases
    #      instead of always returning IntConst for any Primitive type;
    #      e.g. return UIntConst for unsigned integer types, FloatConst for
    #      float types, and possibly things like CharConst UniCharConst etc.
    #      based on what T is (the same kind of checks as in kindToken())
    # -ER- extended genconst()

    test_char_array = skip
    test_char_varsize_array = skip
    test_unichar_array = skip
    test_char_unichar_fields = skip


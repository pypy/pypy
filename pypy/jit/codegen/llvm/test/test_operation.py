import py
from pypy.jit.codegen.i386.test.test_operation import TestBasic
from pypy.jit.codegen.llvm.rgenop import RLLVMGenOp

py.test.skip("WIP")

class LLVMTestBasic(TestBasic):
    RGenOp = RLLVMGenOp

    # for the individual tests see
    # ====> ../../../i386/test/test_operation.py

    pass


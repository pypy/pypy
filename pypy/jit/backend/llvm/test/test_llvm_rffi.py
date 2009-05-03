
from pypy.jit.backend.llvm.llvm_rffi import *

def test_basic():
    LLVMModuleCreateWithName("hello")

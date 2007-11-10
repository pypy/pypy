import py
from pypy.rpython.test.test_rbuiltin import BaseTestRbuiltin
from pypy.translator.llvm.test.runtest import *
py.test.skip("skip these until we have resolved most external functions issues")

class TestLLVMBuiltin(LLVMTest, BaseTestRbuiltin):
    pass

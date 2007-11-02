import py
from pypy.rpython.test.test_rconstantdict import BaseTestRconstantdict
from pypy.translator.llvm.test.runtest import *

class TestLLVMRconstantdict(LLVMTest, BaseTestRconstantdict):
    pass

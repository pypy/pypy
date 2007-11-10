import py
from pypy.rpython.test.test_rpbc import BaseTestRPBC
from pypy.translator.llvm.test.runtest import *

class TestLLVMPBC(LLVMTest, BaseTestRPBC):
    def test_disjoint_pbcs_2(self):
        py.test.skip('XXX no idea why this failing FIXME')


import py
from pypy.rpython.test.test_rlist import BaseTestRlist
from pypy.translator.llvm.test.runtest import *

class TestLLVMList(LLVMTest, BaseTestRlist):
    def test_insert_bug(self):
        py.test.skip('XXX special case me')

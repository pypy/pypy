import py
from pypy.rpython.test.test_rstr import BaseTestRstr
from pypy.translator.llvm.test.runtest import *

class TestLLVMStr(LLVMTest, BaseTestRstr):
    def test_int(self):
        py.test.skip('XXX special case me')

    def test_float(self):
        py.test.skip('XXX special case me')

    def test_hash(self):
        py.test.skip('XXX special case me')



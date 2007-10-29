import py
from pypy.translator.oosupport.test_template.runtest import BaseTestRunTest
from pypy.translator.llvm.test.runtest import *

class TestRunTest(BaseTestRunTest, LLVMTest):
    def test_none(self):
        def fn(x):
            y = 1 + x
            return None
        assert self.interpret(fn,[1]) == None

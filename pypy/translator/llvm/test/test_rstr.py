import py
from pypy.rpython.test.test_rstr import BaseTestRstr
from pypy.translator.llvm.test.runtest import *

# ====> ../../../rpython/test/test_rstr.py

class TestLLVMStr(LLVMTest, BaseTestRstr):
    EMPTY_STRING_HASH = -1

    def test_int(self):
        py.test.skip('XXX special case me')

    def test_float(self):
        py.test.skip('XXX special case me')

    def test_inplace_add(self):
        py.test.skip('XXX special case me')


import py
from pypy.rpython.test.test_rbuiltin import BaseTestRbuiltin

from pypy.translator.llvm.test.runtest import *

class TestLLVMBuiltin(LLVMTest, BaseTestRbuiltin):
    def _skip(self):
        py.test.skip("XXX specialize this")

    test_os_dup = _skip
    test_os_open = _skip
    test_debug_llinterpcall = _skip

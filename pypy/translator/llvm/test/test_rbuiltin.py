import py
from pypy.rpython.test.test_rbuiltin import BaseTestRbuiltin

from pypy.translator.llvm.test.runtest import *

class TestLLVMBuiltin(LLVMTest, BaseTestRbuiltin):
    def _isolate_skip(self):
        py.test.skip("XXX isolate specialize this")

    def _skip(self):
        py.test.skip("XXX specialize this")

    test_os_write = _isolate_skip
    test_os_write_single_char = _isolate_skip
    test_os_dup = _skip
    test_os_open = _skip
    test_debug_llinterpcall = _skip

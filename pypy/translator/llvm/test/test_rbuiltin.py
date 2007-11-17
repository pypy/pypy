import py
from pypy.rpython.test.test_rbuiltin import BaseTestRbuiltin
from pypy.translator.llvm.test.runtest import *

class TestLLVMBuiltin(LLVMTest, BaseTestRbuiltin):
    def _skip_llinterpreter(self):
        LLVMTest._skip_llinterpreter(self)
    test_os_open = _skip_llinterpreter
    test_debug_llinterpcall = _skip_llinterpreter

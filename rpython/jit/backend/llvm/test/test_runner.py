from rpython.jit.backend.test.runner_test import LLtypeBackendTest
from rpython.jit.backend.llvm.runner import LLVM_CPU

class FakeStats(object):
    pass

class TestLLVM(LLtypeBackendTest):
    def get_cpu(self):
        cpu = LLVM_CPU(rtyper=None, stats=FakeStats())
        cpu.setup_once()
        return cpu

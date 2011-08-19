from pypy.jit.backend.test.runner_test import LLtypeBackendTest
from pypy.jit.backend.ppc.runner import PPC_64_CPU

class FakeStats(object):
    pass

class TestPPC(LLtypeBackendTest):
    
    def setup_method(self, method):
        self.cpu = PPC_64_CPU(rtyper=None, stats=FakeStats())
        self.cpu.setup_once()

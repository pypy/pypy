from pypy.jit.backend.test.runner_test import LLtypeBackendTest
from pypy.jit.backend.ppc.runner import PPC_64_CPU
import py

class FakeStats(object):
    pass

class TestPPC(LLtypeBackendTest):
   
    def setup_class(cls):
        cls.cpu = PPC_64_CPU(rtyper=None, stats=FakeStats())
        cls.cpu.setup_once()

    def test_cond_call_gc_wb_array_card_marking_fast_path(self):
        py.test.skip("unsure what to do here")

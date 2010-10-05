from pypy.jit.backend.arm.runner import ArmCPU
from pypy.jit.backend.test.runner_test import LLtypeBackendTest

class FakeStats(object):
    pass

class TestARM(LLtypeBackendTest):

    # for the individual tests see
    # ====> ../../test/runner_test.py

    def setup_method(self, meth):
        self.cpu = ArmCPU(rtyper=None, stats=FakeStats())

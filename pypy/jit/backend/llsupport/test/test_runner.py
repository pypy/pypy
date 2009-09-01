import py
from pypy.jit.backend.llsupport.llmodel import AbstractLLCPU
from pypy.jit.backend.test.runner_test import LLtypeBackendTest


class FakeStats(object):
    pass

class MyLLCPU(AbstractLLCPU):
    def compile_operations(self, loop, guard_op=None):
        py.test.skip("llsupport test: cannot compile operations")


class TestAbstractLLCPU(LLtypeBackendTest):

    # for the individual tests see
    # ====> ../../test/runner_test.py
    
    def setup_class(cls):
        cls.cpu = MyLLCPU(rtyper=None, stats=FakeStats())

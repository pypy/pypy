import py, sys
from pypy.jit.backend.llsupport.llmodel import AbstractLLCPU
from pypy.jit.backend.test.runner_test import LLtypeBackendTest


class FakeStats(object):
    pass

class MyLLCPU(AbstractLLCPU):
    supports_floats = True

    def __init__(self, *args, **kwds):
        super(MyLLCPU, self).__init__(*args, **kwds)
        self.gc_ll_descr.is_compressed_ptr = (
            lambda size: sys.maxint > 2147483647 and size == 4)

    def compile_loop(self, inputargs, operations, looptoken):
        py.test.skip("llsupport test: cannot compile operations")


class TestAbstractLLCPU(LLtypeBackendTest):

    # for the individual tests see
    # ====> ../../test/runner_test.py
    
    def setup_class(cls):
        cls.cpu = MyLLCPU(rtyper=None, stats=FakeStats(), opts=None)

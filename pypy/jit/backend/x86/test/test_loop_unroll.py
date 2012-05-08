import py
from pypy.jit.backend.x86.test.test_basic import Jit386Mixin
from pypy.jit.metainterp.test import test_loop_unroll

class TestLoopSpec(Jit386Mixin, test_loop_unroll.LoopUnrollTest):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_loop.py
    pass

class TestLoopNoRewrite(test_loop_unroll.LoopUnrollTest, Jit386Mixin):
    enable_opts = 'intbounds:virtualize:string:earlyforce:pure:heap:ffi:unroll'
    def check_resops(self, *args, **kwargs):
        pass
    def check_trace_count(self, count):
        pass

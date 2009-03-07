
import py
from pypy.jit.metainterp.test.test_send import SendTests
from pypy.jit.backend.x86.test.test_basic import Jit386Mixin
from pypy.jit.metainterp.policy import StopAtXPolicy

class TestSend(Jit386Mixin, SendTests):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_send.py
    def test_call_with_additional_args(self):
        def externfn(a, b, c, d):
            return a + b*10 + c*100 + d*1000
        def f(a, b, c, d):
            return externfn(a, b, c, d)
        res = self.interp_operations(f, [1, 2, 3, 4],
                                     policy=StopAtXPolicy(externfn))
        assert res == 4321

    

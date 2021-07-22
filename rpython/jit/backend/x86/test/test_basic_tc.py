import py
from rpython.jit.backend.detect_cpu import getcpuclass
from rpython.jit.metainterp.warmspot import ll_meta_interp
from rpython.jit.metainterp.test import support, test_threaded_code
from rpython.jit.codewriter.policy import StopAtXPolicy
from rpython.rlib.jit import JitDriver

class Jit386Mixin(support.LLJitMixin):
    CPUClass = getcpuclass()
    # we have to disable unroll
    enable_opts = "intbounds:rewrite:virtualize:string:earlyforce:pure:heap"
    basic = False

    def check_jumps(self, maxcount):
        pass

class TestBasic(Jit386Mixin, test_threaded_code.BasicTests):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_ajit.py
    pass

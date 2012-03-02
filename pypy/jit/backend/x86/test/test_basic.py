import py
from pypy.jit.backend.detect_cpu import getcpuclass
from pypy.jit.metainterp.warmspot import ll_meta_interp
from pypy.jit.metainterp.test import support, test_ajit
from pypy.jit.codewriter.policy import StopAtXPolicy
from pypy.rlib.jit import JitDriver

class Jit386Mixin(support.LLJitMixin):
    type_system = 'lltype'
    CPUClass = getcpuclass()

    def check_jumps(self, maxcount):
        pass

class TestBasic(Jit386Mixin, test_ajit.BaseLLtypeTests):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_basic.py
    def test_bug(self):
        jitdriver = JitDriver(greens = [], reds = ['n'])
        class X(object):
            pass
        def f(n):
            while n > -100:
                jitdriver.can_enter_jit(n=n)
                jitdriver.jit_merge_point(n=n)
                x = X()
                x.arg = 5
                if n <= 0: break
                n -= x.arg
                x.arg = 6   # prevents 'x.arg' from being annotated as constant
            return n
        res = self.meta_interp(f, [31], enable_opts='')
        assert res == -4

    def test_r_dict(self):
        # a Struct that belongs to the hash table is not seen as being
        # included in the larger Array
        py.test.skip("issue with ll2ctypes")

    def test_free_object(self):
        py.test.skip("issue of freeing, probably with ll2ctypes")

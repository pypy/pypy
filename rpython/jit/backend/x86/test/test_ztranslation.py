import py, os, sys
from rpython.tool.udir import udir
from rpython.rlib.jit import JitDriver, unroll_parameters, set_param
from rpython.rlib.jit import PARAMETERS, dont_look_inside
from rpython.rlib.jit import promote
from rpython.rlib import jit_hooks
from rpython.jit.metainterp.jitprof import Profiler
from rpython.jit.backend.detect_cpu import getcpuclass
from rpython.jit.backend.test.support import CCompiledMixin
from rpython.jit.codewriter.policy import StopAtXPolicy
from rpython.translator.translator import TranslationContext
from rpython.jit.backend.x86.arch import IS_X86_32, IS_X86_64
from rpython.config.translationoption import DEFL_GC
from rpython.rlib import rgc

class TestTranslationX86(CCompiledMixin):
    CPUClass = getcpuclass()

    def _check_cbuilder(self, cbuilder):
        # We assume here that we have sse2.  If not, the CPUClass
        # needs to be changed to CPU386_NO_SSE2, but well.
        assert '-msse2' in cbuilder.eci.compile_extra
        assert '-mfpmath=sse' in cbuilder.eci.compile_extra

    def test_jit_get_stats(self):
        driver = JitDriver(greens = [], reds = ['i'])
        
        def f():
            i = 0
            while i < 100000:
                driver.jit_merge_point(i=i)
                i += 1

        def main():
            jit_hooks.stats_set_debug(None, True)
            f()
            ll_times = jit_hooks.stats_get_loop_run_times(None)
            return len(ll_times)

        res = self.meta_interp(main, [])
        assert res == 3
        # one for loop, one for entry point and one for the prologue

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

    def test_direct_assembler_call_translates(self):
        """Test CALL_ASSEMBLER and the recursion limit"""
        from rpython.rlib.rstackovf import StackOverflow

        class Thing(object):
            def __init__(self, val):
                self.val = val

        class Frame(object):
            _virtualizable2_ = ['thing']

        driver = JitDriver(greens = ['codeno'], reds = ['i', 'frame'],
                           virtualizables = ['frame'],
                           get_printable_location = lambda codeno: str(codeno))
        class SomewhereElse(object):
            pass

        somewhere_else = SomewhereElse()

        def change(newthing):
            somewhere_else.frame.thing = newthing

        def main(codeno):
            frame = Frame()
            somewhere_else.frame = frame
            frame.thing = Thing(0)
            portal(codeno, frame)
            return frame.thing.val

        def portal(codeno, frame):
            i = 0
            while i < 10:
                driver.can_enter_jit(frame=frame, codeno=codeno, i=i)
                driver.jit_merge_point(frame=frame, codeno=codeno, i=i)
                nextval = frame.thing.val
                if codeno == 0:
                    subframe = Frame()
                    subframe.thing = Thing(nextval)
                    nextval = portal(1, subframe)
                elif frame.thing.val > 40:
                    change(Thing(13))
                    nextval = 13
                frame.thing = Thing(nextval + 1)
                i += 1
            return frame.thing.val

        driver2 = JitDriver(greens = [], reds = ['n'])

        def main2(bound):
            try:
                while portal2(bound) == -bound+1:
                    bound *= 2
            except StackOverflow:
                pass
            return bound

        def portal2(n):
            while True:
                driver2.jit_merge_point(n=n)
                n -= 1
                if n <= 0:
                    return n
                n = portal2(n)
        assert portal2(10) == -9

        def mainall(codeno, bound):
            return main(codeno) + main2(bound)

        res = self.meta_interp(mainall, [0, 1], inline=True,
                               policy=StopAtXPolicy(change))
        print hex(res)
        assert res & 255 == main(0)
        bound = res & ~255
        assert 1024 <= bound <= 131072
        assert bound & (bound-1) == 0       # a power of two

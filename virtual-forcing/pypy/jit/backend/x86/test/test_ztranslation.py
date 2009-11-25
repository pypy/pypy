import py
from pypy.rlib.jit import JitDriver, OPTIMIZER_FULL, unroll_parameters
from pypy.rlib.jit import PARAMETERS, dont_look_inside
from pypy.jit.metainterp.jitprof import Profiler
from pypy.jit.backend.x86.runner import CPU386
from pypy.jit.backend.test.support import CCompiledMixin

class TestTranslationX86(CCompiledMixin):
    CPUClass = CPU386

    def test_stuff_translates(self):
        # this is a basic test that tries to hit a number of features and their
        # translation:
        # - jitting of loops and bridges
        # - virtualizables
        # - set_param interface
        # - profiler
        # - full optimizer

        class Frame(object):
            _virtualizable2_ = ['i']

            def __init__(self, i):
                self.i = i

        jitdriver = JitDriver(greens = [], reds = ['frame', 'total'],
                              virtualizables = ['frame'])
        def f(i):
            for param in unroll_parameters:
                defl = PARAMETERS[param]
                jitdriver.set_param(param, defl)
            jitdriver.set_param("threshold", 3)
            jitdriver.set_param("trace_eagerness", 2)
            total = 0
            frame = Frame(i)
            while frame.i > 3:
                jitdriver.can_enter_jit(frame=frame, total=total)
                jitdriver.jit_merge_point(frame=frame, total=total)
                total += frame.i
                if frame.i >= 20:
                    frame.i -= 2
                frame.i -= 1
            return total * 10
        res = self.meta_interp(f, [40])
        assert res == f(40)

    def test_external_exception_handling_translates(self):
        jitdriver = JitDriver(greens = [], reds = ['n', 'total'])

        @dont_look_inside
        def f(x):
            if x > 20:
                return 2
            raise ValueError
        @dont_look_inside
        def g(x):
            if x > 15:
                raise ValueError
            return 2
        def main(i):
            jitdriver.set_param("threshold", 3)
            jitdriver.set_param("trace_eagerness", 2)
            total = 0
            n = i
            while n > 3:
                jitdriver.can_enter_jit(n=n, total=total)
                jitdriver.jit_merge_point(n=n, total=total)
                try:
                    total += f(n)
                except ValueError:
                    total += 1
                try:
                    total += g(n)
                except ValueError:
                    total -= 1
                n -= 1
            return total * 10
        res = self.meta_interp(main, [40])
        assert res == main(40)

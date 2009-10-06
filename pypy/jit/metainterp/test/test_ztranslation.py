import py
from pypy.jit.metainterp.warmspot import rpython_ll_meta_interp, ll_meta_interp
from pypy.jit.metainterp.test import test_basic
from pypy.jit.backend.llgraph import runner
from pypy.rlib.jit import JitDriver, OPTIMIZER_FULL, unroll_parameters, PARAMETERS
from pypy.jit.conftest import option
from pypy.jit.metainterp.jitprof import Profiler

class TranslationTest:

    CPUClass = None
    type_system = None

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
        res = ll_meta_interp(f, [40], CPUClass=self.CPUClass,
                             type_system=self.type_system)
        assert res == f(40)
        from pypy.jit.metainterp import optimize
        res = rpython_ll_meta_interp(f, [40], loops=2, CPUClass=self.CPUClass,
                                     type_system=self.type_system,
                                     optimizer=OPTIMIZER_FULL,
                                     ProfilerClass=Profiler)
        assert res == f(40)


class TestTranslationLLtype(TranslationTest):

    CPUClass = runner.LLtypeCPU
    type_system = 'lltype'

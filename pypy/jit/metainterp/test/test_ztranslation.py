import py
from pypy.jit.metainterp.warmspot import rpython_ll_meta_interp, ll_meta_interp
from pypy.jit.backend.llgraph import runner
from pypy.rlib.jit import JitDriver, OPTIMIZER_FULL, unroll_parameters
from pypy.rlib.jit import PARAMETERS, dont_look_inside
from pypy.jit.metainterp.jitprof import Profiler
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.ootypesystem import ootype

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
        # - jitdriver hooks

        class Frame(object):
            _virtualizable2_ = ['i']

            def __init__(self, i):
                self.i = i

        class JitCellCache:
            entry = None
        jitcellcache = JitCellCache()
        def set_jitcell_at(entry):
            jitcellcache.entry = entry
        def get_jitcell_at():
            return jitcellcache.entry
        def get_printable_location():
            return '(hello world)'
        def can_inline():
            return False

        jitdriver = JitDriver(greens = [], reds = ['frame', 'total'],
                              virtualizables = ['frame'],
                              get_jitcell_at=get_jitcell_at,
                              set_jitcell_at=set_jitcell_at,
                              get_printable_location=get_printable_location,
                              can_inline=can_inline)
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
        res = rpython_ll_meta_interp(f, [40], loops=2, CPUClass=self.CPUClass,
                                     type_system=self.type_system,
                                     optimizer=OPTIMIZER_FULL,
                                     ProfilerClass=Profiler)
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
        res = ll_meta_interp(main, [40], CPUClass=self.CPUClass,
                             type_system=self.type_system)
        assert res == main(40)
        res = rpython_ll_meta_interp(main, [40], loops=2, CPUClass=self.CPUClass,
                                     type_system=self.type_system,
                                     optimizer=OPTIMIZER_FULL,
                                     ProfilerClass=Profiler)
        assert res == main(40)



class TestTranslationLLtype(TranslationTest):

    CPUClass = runner.LLtypeCPU
    type_system = 'lltype'

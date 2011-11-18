import py
from pypy.jit.metainterp.warmspot import rpython_ll_meta_interp, ll_meta_interp
from pypy.jit.backend.llgraph import runner
from pypy.rlib.jit import JitDriver, unroll_parameters, set_param
from pypy.rlib.jit import PARAMETERS, dont_look_inside, hint
from pypy.jit.metainterp.jitprof import Profiler
from pypy.rpython.lltypesystem import lltype, llmemory

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
        # - two JITs
        # - string concatenation, slicing and comparison

        class Frame(object):
            _virtualizable2_ = ['l[*]']

            def __init__(self, i):
                self = hint(self, fresh_virtualizable=True,
                            access_directly=True)
                self.l = [i]

        class OtherFrame(object):
            _virtualizable2_ = ['i', 'l[*]']

            def __init__(self, i):
                self = hint(self, fresh_virtualizable=True,
                            access_directly=True)
                self.i = i
                self.l = [float(i)]

        class JitCellCache:
            entry = None
        jitcellcache = JitCellCache()
        def set_jitcell_at(entry):
            jitcellcache.entry = entry
        def get_jitcell_at():
            return jitcellcache.entry
        def get_printable_location():
            return '(hello world)'

        jitdriver = JitDriver(greens = [], reds = ['total', 'frame'],
                              virtualizables = ['frame'],
                              get_jitcell_at=get_jitcell_at,
                              set_jitcell_at=set_jitcell_at,
                              get_printable_location=get_printable_location)
        def f(i):
            for param, defl in unroll_parameters:
                set_param(jitdriver, param, defl)
            set_param(jitdriver, "threshold", 3)
            set_param(jitdriver, "trace_eagerness", 2)
            total = 0
            frame = Frame(i)
            while frame.l[0] > 3:
                jitdriver.can_enter_jit(frame=frame, total=total)
                jitdriver.jit_merge_point(frame=frame, total=total)
                total += frame.l[0]
                if frame.l[0] >= 20:
                    frame.l[0] -= 2
                frame.l[0] -= 1
            return total * 10
        #
        myjitdriver2 = JitDriver(greens = ['g'],
                                 reds = ['m', 's', 'f', 'float_s'],
                                 virtualizables = ['f'])
        def f2(g, m, x):
            s = ""
            f = OtherFrame(x)
            float_s = 0.0
            while m > 0:
                myjitdriver2.can_enter_jit(g=g, m=m, f=f, s=s, float_s=float_s)
                myjitdriver2.jit_merge_point(g=g, m=m, f=f, s=s,
                                             float_s=float_s)
                s += 'xy'
                if s[:2] == 'yz':
                    return -666
                m -= 1
                f.i += 3
                float_s += f.l[0]
            return f.i
        #
        def main(i, j):
            return f(i) - f2(i+j, i, j)
        res = ll_meta_interp(main, [40, 5], CPUClass=self.CPUClass,
                             type_system=self.type_system,
                             listops=True)
        assert res == main(40, 5)
        res = rpython_ll_meta_interp(main, [40, 5],
                                     CPUClass=self.CPUClass,
                                     type_system=self.type_system,
                                     ProfilerClass=Profiler,
                                     listops=True)
        assert res == main(40, 5)

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
            set_param(jitdriver, "threshold", 3)
            set_param(jitdriver, "trace_eagerness", 2)
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
        res = rpython_ll_meta_interp(main, [40], CPUClass=self.CPUClass,
                                     type_system=self.type_system,
                                     enable_opts='',
                                     ProfilerClass=Profiler)
        assert res == main(40)

class TestTranslationLLtype(TranslationTest):

    CPUClass = runner.LLtypeCPU
    type_system = 'lltype'

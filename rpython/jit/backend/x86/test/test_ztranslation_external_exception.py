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


class TestTranslationRemoveTypePtrX86(CCompiledMixin):
    CPUClass = getcpuclass()

    def _get_TranslationContext(self):
        t = TranslationContext()
        t.config.translation.gc = DEFL_GC   # 'hybrid' or 'minimark'
        t.config.translation.gcrootfinder = 'asmgcc'
        t.config.translation.list_comprehension_operations = True
        t.config.translation.gcremovetypeptr = True
        return t

    def test_external_exception_handling_translates(self):
        jitdriver = JitDriver(greens = [], reds = ['n', 'total'])

        class ImDone(Exception):
            def __init__(self, resvalue):
                self.resvalue = resvalue

        @dont_look_inside
        def f(x, total):
            if x <= 30:
                raise ImDone(total * 10)
            if x > 200:
                return 2
            raise ValueError
        @dont_look_inside
        def g(x):
            if x > 150:
                raise ValueError
            return 2
        class Base:
            def meth(self):
                return 2
        class Sub(Base):
            def meth(self):
                return 1
        @dont_look_inside
        def h(x):
            if x < 20000:
                return Sub()
            else:
                return Base()
        def myportal(i):
            set_param(jitdriver, "threshold", 3)
            set_param(jitdriver, "trace_eagerness", 2)
            total = 0
            n = i
            while True:
                jitdriver.can_enter_jit(n=n, total=total)
                jitdriver.jit_merge_point(n=n, total=total)
                try:
                    total += f(n, total)
                except ValueError:
                    total += 1
                try:
                    total += g(n)
                except ValueError:
                    total -= 1
                n -= h(n).meth()   # this is to force a GUARD_CLASS
        def main(i):
            try:
                myportal(i)
            except ImDone, e:
                return e.resvalue

        # XXX custom fishing, depends on the exact env var and format
        logfile = udir.join('test_ztranslation.log')
        os.environ['PYPYLOG'] = 'jit-log-opt:%s' % (logfile,)
        try:
            res = self.meta_interp(main, [400])
            assert res == main(400)
        finally:
            del os.environ['PYPYLOG']

        guard_class = 0
        for line in open(str(logfile)):
            if 'guard_class' in line:
                guard_class += 1
        # if we get many more guard_classes, it means that we generate
        # guards that always fail (the following assert's original purpose
        # is to catch the following case: each GUARD_CLASS is misgenerated
        # and always fails with "gcremovetypeptr")
        assert 0 < guard_class < 10

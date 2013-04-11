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
from rpython.jit.backend.x86.test.test_ztranslation import fix_annotator_for_vrawbuffer

class TestTranslationX86(CCompiledMixin):
    CPUClass = getcpuclass()

    def _check_cbuilder(self, cbuilder):
        # We assume here that we have sse2.  If not, the CPUClass
        # needs to be changed to CPU386_NO_SSE2, but well.
        assert '-msse2' in cbuilder.eci.compile_extra
        assert '-mfpmath=sse' in cbuilder.eci.compile_extra

    def test_stuff_translates(self, monkeypatch):
        # this is a basic test that tries to hit a number of features and their
        # translation:
        # - jitting of loops and bridges
        # - virtualizables
        # - set_param interface
        # - profiler
        # - full optimizer
        # - floats neg and abs
        fix_annotator_for_vrawbuffer(monkeypatch)

        class Frame(object):
            _virtualizable2_ = ['i']

            def __init__(self, i):
                self.i = i

        @dont_look_inside
        def myabs(x):
            return abs(x)

        jitdriver = JitDriver(greens = [],
                              reds = ['total', 'frame', 'j'],
                              virtualizables = ['frame'])
        def f(i, j):
            for param, _ in unroll_parameters:
                defl = PARAMETERS[param]
                set_param(jitdriver, param, defl)
            set_param(jitdriver, "threshold", 3)
            set_param(jitdriver, "trace_eagerness", 2)
            total = 0
            frame = Frame(i)
            j = float(j)
            while frame.i > 3:
                jitdriver.can_enter_jit(frame=frame, total=total, j=j)
                jitdriver.jit_merge_point(frame=frame, total=total, j=j)
                total += frame.i
                if frame.i >= 20:
                    frame.i -= 2
                frame.i -= 1
                j *= -0.712
                if j + (-j):    raise ValueError
                k = myabs(j)
                if k - abs(j):  raise ValueError
                if k - abs(-j): raise ValueError
            return chr(total % 253)
        #
        from rpython.rtyper.lltypesystem import lltype, rffi
        from rpython.rlib.libffi import types, CDLL, ArgChain
        from rpython.rlib.test.test_clibffi import get_libm_name
        libm_name = get_libm_name(sys.platform)
        jitdriver2 = JitDriver(greens=[], reds = ['i', 'func', 'res', 'x'])
        def libffi_stuff(i, j):
            lib = CDLL(libm_name)
            func = lib.getpointer('fabs', [types.double], types.double)
            res = 0.0
            x = float(j)
            while i > 0:
                jitdriver2.jit_merge_point(i=i, res=res, func=func, x=x)
                promote(func)
                argchain = ArgChain()
                argchain.arg(x)
                res = func.call(argchain, rffi.DOUBLE)
                i -= 1
            return res
        #
        def main(i, j):
            a_char = f(i, j)
            a_float = libffi_stuff(i, j)
            return ord(a_char) * 10 + int(a_float)
        expected = main(40, -49)
        res = self.meta_interp(main, [40, -49])
        assert res == expected

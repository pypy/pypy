import py
from pypy.jit.backend.minimal.runner import LLtypeCPU, OOtypeCPU
from pypy.jit.backend.test.support import CCompiledMixin, CliCompiledMixin
from pypy.jit.metainterp.test import test_zrpy_exception

class LLTranslatedJitMixin(CCompiledMixin):
    CPUClass = LLtypeCPU

    def meta_interp(self, *args, **kwds):
        from pypy.jit.metainterp.simple_optimize import Optimizer
        kwds['optimizer'] = Optimizer
        return CCompiledMixin.meta_interp(self, *args, **kwds)


class OOTranslatedJitMixin(CliCompiledMixin):
    CPUClass = OOtypeCPU

    def meta_interp(self, *args, **kwds):
        from pypy.jit.metainterp.simple_optimize import Optimizer
        kwds['optimizer'] = Optimizer
        return CliCompiledMixin.meta_interp(self, *args, **kwds)


class TestOOtype(OOTranslatedJitMixin, test_zrpy_exception.TestLLExceptions):

    def skip(self):
        py.test.skip('in-progress')

    test_bridge_from_interpreter_exc = skip
    test_bridge_from_interpreter_exc_2 = skip
    test_raise = skip
    test_raise_through = skip
    test_raise_through_wrong_exc = skip
    test_raise_through_wrong_exc_2 = skip



class TestLLtype(LLTranslatedJitMixin, test_zrpy_exception.TestLLExceptions):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_exception.py
    pass

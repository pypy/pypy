import py
from pypy.jit.backend.minimal.runner import LLtypeCPU, OOtypeCPU
from pypy.jit.backend.test.support import CCompiledMixin, CliCompiledMixin
from pypy.jit.metainterp.test import test_zrpy_exception

class LLTranslatedJitMixin(CCompiledMixin):
    CPUClass = LLtypeCPU

    def meta_interp(self, *args, **kwds):
        py.test.skip("skipped for now")
        from pypy.jit.metainterp import simple_optimize
        kwds['optimizer'] = simple_optimize
        return CCompiledMixin.meta_interp(self, *args, **kwds)


class OOTranslatedJitMixin(CliCompiledMixin):
    CPUClass = OOtypeCPU

    def meta_interp(self, *args, **kwds):
        py.test.skip("skipped for now")
        from pypy.jit.metainterp import simple_optimize
        kwds['optimizer'] = simple_optimize
        return CliCompiledMixin.meta_interp(self, *args, **kwds)


class TestOOtype(OOTranslatedJitMixin, test_zrpy_exception.TestLLExceptions):
    pass


class TestLLtype(LLTranslatedJitMixin, test_zrpy_exception.TestLLExceptions):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_exception.py
    pass

import py
from pypy.jit.backend.minimal.runner import LLtypeCPU, OOtypeCPU
from pypy.jit.backend.minimal.support import c_meta_interp
from pypy.jit.metainterp.test import test_basic, test_zrpy_exception


class TranslatedJitMixin(test_basic.LLJitMixin):
    CPUClass = LLtypeCPU

    def meta_interp(self, *args, **kwds):
        return c_meta_interp(*args, **kwds)

    def check_loops(self, *args, **kwds):
        pass
    def check_tree_loop_count(self, *args, **kwds):
        pass
    def check_enter_count(self, *args, **kwds):
        pass
    def check_enter_count_at_most(self, *args, **kwds):
        pass

    def interp_operations(self, *args, **kwds):
        py.test.skip("interp_operations test skipped")


class TestException(TranslatedJitMixin, test_zrpy_exception.TestLLExceptions):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_exception.py
    pass

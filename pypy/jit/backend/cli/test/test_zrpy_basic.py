import py
from pypy.jit.backend.cli.runner import CliCPU
from pypy.jit.backend.test.support import CliCompiledMixin
from pypy.jit.metainterp.test import test_basic

class CliTranslatedJitMixin(CliCompiledMixin):
    CPUClass = CliCPU

    def meta_interp(self, *args, **kwds):
        from pypy.jit.metainterp.simple_optimize import Optimizer
        kwds['optimizer'] = Optimizer
        return CliCompiledMixin.meta_interp(self, *args, **kwds)


class TestBasic(CliTranslatedJitMixin, test_basic.TestOOtype):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_basic.py

    def skip(self):
        py.test.skip('in-progress')

    test_constant_across_mp = skip
    test_stopatxpolicy = skip
    test_print = skip
    test_bridge_from_interpreter = skip
    test_bridge_from_interpreter_2 = skip
    test_bridge_from_interpreter_3 = skip
    test_bridge_from_interpreter_4 = skip

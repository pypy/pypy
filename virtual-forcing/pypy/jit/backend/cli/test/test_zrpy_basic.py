import py
from pypy.jit.backend.cli.runner import CliCPU
from pypy.jit.backend.test.support import CliCompiledMixin
from pypy.jit.metainterp.test import test_basic

class CliTranslatedJitMixin(CliCompiledMixin):
    CPUClass = CliCPU

    def meta_interp(self, *args, **kwds):
        from pypy.rlib.jit import OPTIMIZER_SIMPLE
        kwds['optimizer'] = OPTIMIZER_SIMPLE
        return CliCompiledMixin.meta_interp(self, *args, **kwds)


class TestBasic(CliTranslatedJitMixin, test_basic.TestOOtype):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_basic.py

    def mono_bug(self):
        py.test.skip('mono bug?')

    def skip(self):
        py.test.skip('in-progress')

    test_stopatxpolicy = mono_bug

    test_print = skip
    test_bridge_from_interpreter = skip
    test_bridge_from_interpreter_2 = skip
    test_free_object = skip

    def test_bridge_from_interpreter_4(self):
        pass # not a translation test
    
    def test_we_are_jitted(self):
        py.test.skip("it seems to fail even with the x86 backend, didn't investigate the problem")

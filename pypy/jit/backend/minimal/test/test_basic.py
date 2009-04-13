import py
from pypy.jit.backend.minimal.runner import CPU
from pypy.jit.metainterp.test import test_basic

class JitMixin(test_basic.LLJitMixin):
    type_system = 'lltype'
    CPUClass = CPU

    def check_jumps(self, maxcount):
        pass

class TestBasic(JitMixin, test_basic.BasicTests):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_basic.py
    pass

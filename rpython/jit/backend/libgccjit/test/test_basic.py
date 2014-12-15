import py
from rpython.jit.backend.detect_cpu import getcpuclass
from rpython.jit.metainterp.test import support, test_ajit

class JitLibgccjitMixin(support.LLJitMixin):
    type_system = 'lltype'
    CPUClass = getcpuclass()

    def check_jumps(self, maxcount):
        pass

class TestBasic(JitLibgccjitMixin, test_ajit.BaseLLtypeTests):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_basic.py
    pass

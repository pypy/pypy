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

    def _skip(self):
        py.test.skip("call not supported in non-translated version")

    test_stopatxpolicy = _skip
    test_print = _skip
    test_bridge_from_interpreter_2 = _skip
    test_bridge_from_interpreter_3 = _skip
    test_instantiate_classes = _skip

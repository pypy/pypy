import py
from pypy.jit.metainterp.test.test_basic import BasicTests
from pypy.jit.backend.minimal.test.test_zrpy_exception import LLTranslatedJitMixin, OOTranslatedJitMixin

class TestOOtype(OOTranslatedJitMixin, BasicTests):
    def skip(self):
        py.test.skip('in-progress')

    test_stopatxpolicy = skip
    test_print = skip
    test_bridge_from_interpreter = skip
    test_bridge_from_interpreter_2 = skip


class TestLLtype(LLTranslatedJitMixin, BasicTests):
    def skip(self):
        py.test.skip('in-progress')

    test_print = skip
    test_bridge_from_interpreter = skip
    test_bridge_from_interpreter_2 = skip


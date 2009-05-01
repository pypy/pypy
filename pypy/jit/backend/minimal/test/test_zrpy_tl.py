import py
from pypy.jit.metainterp.test.test_tl import ToyLanguageTests
from pypy.jit.backend.minimal.test.test_zrpy_exception import LLTranslatedJitMixin, OOTranslatedJitMixin

class TestOOtype(OOTranslatedJitMixin, ToyLanguageTests):

    def skip(self):
        py.test.skip('in-progress')
    
    test_tl_base = skip
    test_tl_2 = skip
    test_tl_call = skip


class TestLLtype(LLTranslatedJitMixin, ToyLanguageTests):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_tl.py
    pass

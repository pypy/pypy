import py
from pypy.jit.metainterp.test.test_tl import ToyLanguageTests
from pypy.jit.backend.minimal.test.test_zrpy_exception import LLTranslatedJitMixin

class TestTL(LLTranslatedJitMixin, ToyLanguageTests):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_tl.py
    pass

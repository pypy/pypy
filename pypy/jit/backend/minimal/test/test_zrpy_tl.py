import py
from pypy.jit.metainterp.test.test_tl import ToyLanguageTests
from pypy.jit.backend.minimal.test.test_zrpy_exception import LLTranslatedJitMixin, OOTranslatedJitMixin

class TestOOtype(OOTranslatedJitMixin, ToyLanguageTests):
    
    def test_tl_base(self):
        # XXX: remove this hack as soon as WarmEnterState is no longer a pbc
        from pypy.rlib import jit
        try:
            jit.PARAMETERS['hash_bits'] = 6
            ToyLanguageTests.test_tl_base(self)
        finally:
            jit.PARAMETERS['hash_bits'] = 14

    def test_tl_2(self):
        # XXX: remove this hack as soon as WarmEnterState is no longer a pbc
        from pypy.rlib import jit
        try:
            jit.PARAMETERS['hash_bits'] = 6
            ToyLanguageTests.test_tl_2(self)
        finally:
            jit.PARAMETERS['hash_bits'] = 14

    def test_tl_call(self):
        # XXX: remove this hack as soon as WarmEnterState is no longer a pbc
        from pypy.rlib import jit
        try:
            jit.PARAMETERS['hash_bits'] = 6
            ToyLanguageTests.test_tl_call(self)
        finally:
            jit.PARAMETERS['hash_bits'] = 14



class TestLLtype(LLTranslatedJitMixin, ToyLanguageTests):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_tl.py
    pass

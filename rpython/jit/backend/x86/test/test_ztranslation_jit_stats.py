from rpython.jit.backend.llsupport.test.ztranslation_test import TranslationTestJITStats
from rpython.translator.translator import TranslationContext
from rpython.config.translationoption import DEFL_GC


class TestTranslationJITStatsX86(TranslationTestJITStats):
    def _check_cbuilder(self, cbuilder):
        # We assume here that we have sse2.  If not, the CPUClass
        # needs to be changed to CPU386_NO_SSE2, but well.
        assert '-msse2' in cbuilder.eci.compile_extra
        assert '-mfpmath=sse' in cbuilder.eci.compile_extra
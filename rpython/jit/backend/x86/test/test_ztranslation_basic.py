from rpython.jit.backend.llsupport.test.ztranslation_test import TranslationTest
from rpython.jit.backend.x86.arch import WORD


class TestTranslationX86(TranslationTest):
    def _check_cbuilder(self, cbuilder):
        # We assume here that we have sse2.  If not, the CPUClass
        # needs to be changed to CPU386_NO_SSE2, but well.
        if WORD == 4:
            assert '-msse2' in cbuilder.eci.compile_extra
            assert '-mfpmath=sse' in cbuilder.eci.compile_extra

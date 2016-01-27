from rpython.jit.backend.llsupport.test.ztranslation_test import TranslationTestCallAssembler
from rpython.translator.translator import TranslationContext
from rpython.config.translationoption import DEFL_GC
from rpython.jit.backend.zarch.arch import WORD
import sys

class TestTranslationCallAssemblerZARCH(TranslationTestCallAssembler):
    def _check_cbuilder(self, cbuilder):
        pass


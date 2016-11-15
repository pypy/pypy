from rpython.jit.backend.llsupport.test.ztranslation_test import TranslationRemoveTypePtrTest
from rpython.translator.translator import TranslationContext
from rpython.config.translationoption import DEFL_GC
from rpython.translator.platform import platform as compiler

if compiler.name == 'msvc':
    _MSVC = True
else:
    _MSVC = False

class TestTranslationRemoveTypePtrX86(TranslationRemoveTypePtrTest):
    def _get_TranslationContext(self):
        t = TranslationContext()
        t.config.translation.gc = DEFL_GC   # 'hybrid' or 'minimark'
        if not _MSVC:
            t.config.translation.gcrootfinder = 'asmgcc'
        t.config.translation.list_comprehension_operations = True
        t.config.translation.gcremovetypeptr = True
        return t

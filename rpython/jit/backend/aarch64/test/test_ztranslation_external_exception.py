from rpython.jit.backend.llsupport.test.ztranslation_test import TranslationRemoveTypePtrTest
from rpython.translator.translator import TranslationContext

class TestTranslationRemoveTypePtrAarch64(TranslationRemoveTypePtrTest):
    def _get_TranslationContext(self):
        t = TranslationContext()
        t.config.translation.list_comprehension_operations = True
        t.config.translation.gcremovetypeptr = True
        return t

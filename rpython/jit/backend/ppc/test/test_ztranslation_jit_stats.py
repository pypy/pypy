
import py
py.test.skip("not implemented: get_all_loop_runs()", allow_module_level=True)

from rpython.jit.backend.llsupport.test.ztranslation_test import TranslationTestJITStats


class TestTranslationJITStatsPPC(TranslationTestJITStats):
    pass

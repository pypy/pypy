
""" Tests whether each interpreter translates itself
"""

#def base_translation_test(targetname):

import sys, py
from pypy.translator import driver
from pypy.translator import translator
from pypy.config.translationoption import get_combined_translation_config
from pypy.translator.goal.translate import load_target

class TestTranslation:
    def translate(self, targetname):
        config = get_combined_translation_config(translating=True)
        config.translation.backend = 'c'
        config.translation.gc = 'boehm'
        targetspec = 'pypy.translator.goal.' + targetname
        mod = __import__(targetspec)
        targetspec_dic = sys.modules[targetspec].__dict__
        t = translator.TranslationContext()
        drv = driver.TranslationDriver.from_targetspec(targetspec_dic, config, [],
                                                       empty_translator=t)
        drv.exe_name = None
        drv.proceed('compile')

    def test_scheme(self):
        self.translate('targetscheme')

    def test_js(self):
        self.translate('targetjsstandalone')

    def test_prolog(self):
        self.translate('targetprologstandalone')

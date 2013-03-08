import py
import sys, os
from rpython.translator.c.test import test_standalone

def setup_module(module):
    if sys.platform == 'win32':
        if not ('mingw' in os.popen('gcc --version').read() and
                'GNU' in os.popen('make --version').read()):
            py.test.skip("mingw32 and MSYS are required for asmgcc on Windows")

class TestThreadedAsmGcc(test_standalone.TestThread):
    gcrootfinder = 'asmgcc'

    def setup_class(cls):
        if sys.platform == 'win32':
            from rpython.config.translationoption import get_combined_translation_config
            cls.config = get_combined_translation_config(translating=True)
            cls.config.translation.cc = 'mingw32'

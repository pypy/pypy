import platform
import py
from pypy.translator.cli.test.runtest import CliTest
from pypy.translator.oosupport.test_template.builtin import BaseTestBuiltin, BaseTestTime


def skip_os(self):
    py.test.skip("CLI doesn't support the os module, yet")

def skip_win():
    if platform.system() == 'Windows':
        py.test.skip("Doesn't work on Windows, yet")

class TestCliBuiltin(CliTest, BaseTestBuiltin):
    test_os_path_exists = skip_os
    test_os_isdir = skip_os
    test_os_dup_oo = skip_os

        
    def test_builtin_math_frexp(self):
        self._skip_powerpc("Mono math floating point problem")
        BaseTestBuiltin.test_builtin_math_frexp(self)

    def test_debug_llinterpcall(self):
        py.test.skip("so far, debug_llinterpcall is only used on lltypesystem")


class TestCliTime(CliTest, BaseTestTime):
    pass

import py
from pypy.translator.cli.test.runtest import CliTest
from pypy.rpython.test.test_rbuiltin import BaseTestRbuiltin

def skip_math_os(self):
    py.test.skip("CLI doesn't support math and os module, yet")

class TestCliBuiltin(CliTest, BaseTestRbuiltin):
    test_builtin_math_floor = skip_math_os
    test_builtin_math_fmod = skip_math_os
    test_builtin_math_frexp = skip_math_os
    test_builtin_math_modf = skip_math_os
    test_os_getcwd = skip_math_os
    test_os_write = skip_math_os
    test_os_write_single_char = skip_math_os
    test_os_read = skip_math_os
    test_os_dup = skip_math_os
    test_os_open = skip_math_os
    test_os_path_exists = skip_math_os
    test_os_isdir = skip_math_os

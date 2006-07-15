import py
from pypy.translator.cli.test.runtest import CliTest
from pypy.rpython.test.test_rbuiltin import BaseTestRbuiltin

def skip_os(self):
    py.test.skip("CLI doesn't support the os module, yet")

class TestCliBuiltin(CliTest, BaseTestRbuiltin):
    test_os_getcwd = skip_os
    test_os_write = skip_os
    test_os_write_single_char = skip_os
    test_os_read = skip_os
    test_os_dup = skip_os
    test_os_open = skip_os
    test_os_path_exists = skip_os
    test_os_isdir = skip_os


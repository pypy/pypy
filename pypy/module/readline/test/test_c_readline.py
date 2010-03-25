"""
Directly test the basic ctypes wrappers.
"""

import py
from pypy import conftest; conftest.translation_test_so_skip_if_appdirect()
from pypy.rpython.tool import rffi_platform as platform

try:
    from pypy.module.readline import c_readline
except platform.CompilationError, e:
    py.test.skip(e)


def test_basic_import():
    c_readline.c_rl_initialize()

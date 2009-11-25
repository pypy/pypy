"""
Directly test the basic ctypes wrappers.
"""

from pypy import conftest; conftest.translation_test_so_skip_if_appdirect()
from pypy.module.readline import c_readline 


def test_basic_import():
    c_readline.c_rl_initialize()

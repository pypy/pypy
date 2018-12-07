"""
A testcase which accesses *values* in a dll.
"""

from ctypes import *
from .support import BaseCTypesTestChecker

def setup_module(mod):
    import conftest
    _ctypes_test = str(conftest.sofile)
    mod.ctdll = CDLL(_ctypes_test)

class TestValues(BaseCTypesTestChecker):

    def test_a_string(self):
        a_string = (c_char * 16).in_dll(ctdll, "a_string")
        assert a_string.raw == "0123456789abcdef"
        a_string[15] = '$'
        assert ctdll.get_a_string_char(15) == ord('$')

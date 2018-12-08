"""
A testcase which accesses *values* in a dll.
"""

from ctypes import *
from .support import BaseCTypesTestChecker

class TestValues(BaseCTypesTestChecker):

    def test_a_string(self, dll):
        a_string = (c_char * 16).in_dll(dll, "a_string")
        assert a_string.raw == "0123456789abcdef"
        a_string[15] = '$'
        assert dll.get_a_string_char(15) == ord('$')

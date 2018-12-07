import pytest
from ctypes import *
import sys
import os, StringIO
from ctypes.util import find_library
from ctypes.test import is_resource_enabled

class TestLoader:

    def test__handle(self):
        lib = find_library("c")
        if lib:
            cdll = CDLL(lib)
            assert type(cdll._handle) in (int, long)

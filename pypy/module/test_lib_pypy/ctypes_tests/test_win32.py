# Windows specific tests

from ctypes import *
from .support import BaseCTypesTestChecker

import pytest
import sys

if sys.platform != "win32":
    pytest.importorskip('skip_the_whole_module')  # hack!

class TestWintypes(BaseCTypesTestChecker):
    def test_VARIANT(self):
        from ctypes import wintypes
        a = wintypes.VARIANT_BOOL()
        assert a.value is False
        b = wintypes.VARIANT_BOOL(3)
        assert b.value is True

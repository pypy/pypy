# Windows specific tests

from ctypes import *
from ctypes.test import is_resource_enabled
from support import BaseCTypesTestChecker

import py
import sys

if sys.platform != "win32":
    py.test.skip("win32-only tests")

class TestWindows(BaseCTypesTestChecker):
    def test_callconv_1(self):
        # Testing stdcall function

        IsWindow = windll.user32.IsWindow
        # ValueError: Procedure probably called with not enough arguments (4 bytes missing)
        py.test.raises(ValueError, IsWindow)

        # This one should succeeed...
        assert IsWindow(0) == 0

        # ValueError: Procedure probably called with too many arguments (8 bytes in excess)
        py.test.raises(ValueError, IsWindow, 0, 0, 0)

    def test_callconv_2(self):
        # Calling stdcall function as cdecl

        IsWindow = cdll.user32.IsWindow

        # ValueError: Procedure called with not enough arguments (4 bytes missing)
        # or wrong calling convention
        py.test.raises(ValueError, IsWindow, None)

    if is_resource_enabled("SEH"):
        def test_SEH(self):
            # Call functions with invalid arguments, and make sure that access violations
            # are trapped and raise an exception.
            py.test.raises(WindowsError, windll.kernel32.GetModuleHandleA, 32)

class TestWintypes(BaseCTypesTestChecker):

    def test_COMError(self):
        import _ctypes
        from _ctypes import COMError
        assert COMError.__doc__ == "Raised when a COM method call failed."

        ex = COMError(-1, "text", ("details",))
        assert ex.hresult == -1
        assert ex.text == "text"
        assert ex.details == ("details",)
        assert (ex.hresult, ex.text, ex.details) == ex[:]

    def test_VARIANT(self):
        from ctypes import wintypes
        a = wintypes.VARIANT_BOOL()
        assert a.value is False
        b = wintypes.VARIANT_BOOL(3)
        assert b.value is True

class TestStructures(BaseCTypesTestChecker):

    def test_struct_by_value(self):
        class POINT(Structure):
            _fields_ = [("x", c_long),
                        ("y", c_long)]

        class RECT(Structure):
            _fields_ = [("left", c_long),
                        ("top", c_long),
                        ("right", c_long),
                        ("bottom", c_long)]

        import conftest
        dll = CDLL(str(conftest.sofile))

        pt = POINT(10, 10)
        rect = RECT(0, 0, 20, 20)
        assert dll.PointInRect(byref(rect), pt) == 1

import py

import ctypes
from _ctypes import function

try:
    import _rawffi
except ImportError:
    py.test.skip("app-level test only for PyPy")

class TestErrno:

    def test_errno_saved_and_restored(self):
        def check():
            assert _rawffi.get_errno() == 42
            assert ctypes.get_errno() == old
        check.free_temp_buffers = lambda *args: None
        f = function.CFuncPtr()
        old = _rawffi.get_errno()
        f._flags_ = _rawffi.FUNCFLAG_USE_ERRNO
        ctypes.set_errno(42)
        f._call_funcptr(check)
        assert _rawffi.get_errno() == old
        ctypes.set_errno(0)

    # see also test_functions.test_errno

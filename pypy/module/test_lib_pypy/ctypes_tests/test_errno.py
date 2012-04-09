import py

import ctypes
from _ctypes import function

_rawffi = py.test.importorskip("_rawffi")

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

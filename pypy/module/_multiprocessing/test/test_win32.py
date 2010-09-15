import py
import sys
from pypy.conftest import gettestobjspace

class AppTestWin32:
    def setup_class(cls):
        if sys.platform != "win32":
            py.test.skip("win32 only")
        cls.space = gettestobjspace(usemodules=('_multiprocessing',))

    def test_CloseHandle(self):
        import _multiprocessing
        raises(WindowsError, _multiprocessing.win32.CloseHandle, -1)

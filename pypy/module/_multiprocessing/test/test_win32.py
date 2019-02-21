import py
import sys

class AppTestWin32:
    spaceconfig = dict(usemodules=('_multiprocessing',
                                   'signal', '_rawffi', 'binascii'))

    def setup_class(cls):
        if sys.platform != "win32":
            py.test.skip("win32 only")

    def test_closesocket(self):
        from _multiprocessing import closesocket
        raises(WindowsError, closesocket, -1)


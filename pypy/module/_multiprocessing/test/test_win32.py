import py
import sys
from pypy.conftest import gettestobjspace

class AppTestWin32:
    def setup_class(cls):
        if sys.platform != "win32":
            py.test.skip("win32 only")
        cls.space = gettestobjspace(usemodules=('_multiprocessing',))

    def test_CloseHandle(self):
        from _multiprocessing import win32
        raises(WindowsError, win32.CloseHandle, -1)

    def test_CreateFile(self):
        from _multiprocessing import win32
        err = raises(WindowsError, win32.CreateFile,
                     "in/valid", 0, 0, 0, 0, 0, 0)
        assert err.value.winerror == 87 # ERROR_INVALID_PARAMETER

    def test_pipe(self):
        from _multiprocessing import win32
        import os
        address = r'\\.\pipe\pypy-test-%s' % (os.getpid())
        openmode = win32.PIPE_ACCESS_INBOUND
        access = win32.GENERIC_WRITE
        obsize, ibsize = 0, 8192
        readhandle = win32.CreateNamedPipe(
            address, openmode,
            win32.PIPE_TYPE_MESSAGE | win32.PIPE_READMODE_MESSAGE |
            win32.PIPE_WAIT,
            1, obsize, ibsize, win32.NMPWAIT_WAIT_FOREVER, win32.NULL
            )
        writehandle = win32.CreateFile(
            address, access, 0, win32.NULL, win32.OPEN_EXISTING, 0, win32.NULL
            )
        win32.SetNamedPipeHandleState(
            writehandle, win32.PIPE_READMODE_MESSAGE, None, None)

        try:
            win32.ConnectNamedPipe(readhandle, win32.NULL)
        except WindowsError, e:
            if e.args[0] != win32.ERROR_PIPE_CONNECTED:
                raise

        timeout = 100
        exc = raises(WindowsError, win32.WaitNamedPipe, address, timeout)
        assert exc.value.winerror == 121 # ERROR_SEM_TIMEOUT

        win32.CloseHandle(readhandle)
        win32.CloseHandle(writehandle)

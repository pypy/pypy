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

    def test_pipe(self):
        import _winapi as win32
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
        except WindowsError as e:
            if e.args[0] != win32.ERROR_PIPE_CONNECTED:
                raise

        timeout = 100
        exc = raises(WindowsError, win32.WaitNamedPipe, address, timeout)
        assert exc.value.winerror == 121 # ERROR_SEM_TIMEOUT

        win32.CloseHandle(readhandle)
        win32.CloseHandle(writehandle)

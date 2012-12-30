import os
if os.name != 'nt':
    skip('tests for win32 only')

from rpython.rlib import rwin32
from pypy.tool.udir import udir


def test_get_osfhandle():
    fid = open(str(udir.join('validate_test.txt')), 'w')
    fd = fid.fileno()
    rwin32.get_osfhandle(fd)
    fid.close()
    raises(OSError, rwin32.get_osfhandle, fd)
    rwin32.get_osfhandle(0)

def test_get_osfhandle_raising():
    #try to test what kind of exception get_osfhandle raises w/out fd validation
    skip('Crashes python')
    fid = open(str(udir.join('validate_test.txt')), 'w')
    fd = fid.fileno()
    fid.close()
    def validate_fd(fd):
        return 1
    _validate_fd = rwin32.validate_fd
    rwin32.validate_fd = validate_fd
    raises(WindowsError, rwin32.get_osfhandle, fd)
    rwin32.validate_fd = _validate_fd

def test_open_process():
    pid = rwin32.GetCurrentProcessId()
    assert pid != 0
    handle = rwin32.OpenProcess(rwin32.PROCESS_QUERY_INFORMATION, False, pid)
    rwin32.CloseHandle(handle)
    raises(WindowsError, rwin32.OpenProcess, rwin32.PROCESS_TERMINATE, False, 0)

def test_terminate_process():
    import subprocess, signal, sys
    proc = subprocess.Popen([sys.executable, "-c",
                         "import time;"
                         "time.sleep(10)",
                         ],
                        ) 
    print proc.pid
    handle = rwin32.OpenProcess(rwin32.PROCESS_ALL_ACCESS, False, proc.pid)
    assert rwin32.TerminateProcess(handle, signal.SIGTERM) == 1
    rwin32.CloseHandle(handle)
    assert proc.wait() == signal.SIGTERM
 

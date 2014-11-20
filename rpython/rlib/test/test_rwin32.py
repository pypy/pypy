# encoding: utf-8
import os, py
if os.name != 'nt':
    py.test.skip('tests for win32 only')

from rpython.rlib import rwin32
from rpython.tool.udir import udir


def test_get_osfhandle():
    fid = open(str(udir.join('validate_test.txt')), 'w')
    fd = fid.fileno()
    rwin32.get_osfhandle(fd)
    fid.close()
    py.test.raises(OSError, rwin32.get_osfhandle, fd)
    rwin32.get_osfhandle(0)

def test_get_osfhandle_raising():
    #try to test what kind of exception get_osfhandle raises w/out fd validation
    py.test.skip('Crashes python')
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
    py.test.raises(WindowsError, rwin32.OpenProcess, rwin32.PROCESS_TERMINATE, False, 0)

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
 
@py.test.mark.dont_track_allocations('putenv intentionally keeps strings alive')
def test_wenviron():
    name, value = u'PYPY_TEST_日本', u'foobar日本'
    rwin32._wputenv(name, value)
    assert rwin32._wgetenv(name) == value
    env = dict(rwin32._wenviron_items())
    assert env[name] == value
    for key, value in env.iteritems():
        assert type(key) is unicode
        assert type(value) is unicode

def test_formaterror():
    # choose one with formatting characters and newlines
    msg = rwin32.FormatError(34)
    assert '%2' in msg


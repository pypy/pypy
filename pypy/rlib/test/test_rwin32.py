import os
if os.name <> 'nt':
    skip('tests for win32 only')

from pypy.rlib import rwin32
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

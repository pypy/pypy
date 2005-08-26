import os
from pypy.tool.udir import udir
from pypy.rpython.module.ll_os import *


def test_open_read_write_close():
    filename = str(udir.join('test_open_read_write_close.txt'))
    rsfilename = to_rstr(filename)

    fd = ll_os_open(rsfilename, os.O_WRONLY | os.O_CREAT, 0777)
    count = ll_os_write(fd, to_rstr("hello world\n"))
    assert count == len("hello world\n")
    ll_os_close(fd)

    fd = ll_os_open(rsfilename, os.O_RDONLY, 0777)
    data = ll_os_read(fd, 500)
    assert from_rstr(data) == "hello world\n"
    ll_os_close(fd)

    os.unlink(filename)


def test_getcwd():
    data = ll_os_getcwd()
    assert from_rstr(data) == os.getcwd()

def test_strerror():
    data = ll_os_strerror(2)
    assert from_rstr(data) == os.strerror(2)

def test_system():
    filename = str(udir.join('test_system.txt'))
    arg = to_rstr('python -c "print 1+1" > %s' % filename)
    data = ll_os_system(arg)
    assert data == 0
    assert file(filename).read().strip() == '2'
    os.unlink(filename)

def test_putenv():
    filename = str(udir.join('test_putenv.txt'))
    arg = to_rstr('abcdefgh=12345678')
    ll_os_putenv(arg)
    cmd = '''python -c "import os; print os.environ['abcdefgh']" > %s''' % filename
    os.system(cmd)
    assert file(filename).read().strip() == '12345678'
    os.unlink(filename)

# XXX missing test for unsetenv, please do this on Linux

def test_environ():
    count = 0
    while 1:
        if not ll_os_environ(count):
            break
        count += 1
    assert count == len(os.environ.keys())

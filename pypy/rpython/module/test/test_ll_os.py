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

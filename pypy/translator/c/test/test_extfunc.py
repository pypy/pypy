import autopath
import py
import os, time
from pypy.tool.udir import udir
from pypy.translator.c.test.test_genc import compile


def test_time_clock():
    def does_stuff():
        return time.clock()
    f1 = compile(does_stuff, [])
    t0 = time.clock()
    t1 = f1()
    assert type(t1) is float
    t2 = time.clock()
    assert t0 <= t1 <= t2


def test_os_open():
    tmpfile = str(udir.join('test_os_open.txt'))
    def does_stuff():
        fd = os.open(tmpfile, os.O_WRONLY | os.O_CREAT, 0777)
        return fd

    f1 = compile(does_stuff, [])
    fd = f1()
    os.close(fd)
    assert os.path.exists(tmpfile)

def test_failing_os_open():
    tmpfile = str(udir.join('test_failing_os_open.DOESNTEXIST'))
    def does_stuff():
        fd = os.open(tmpfile, os.O_RDONLY, 0777)
        return fd

    f1 = compile(does_stuff, [])
    py.test.raises(OSError, f1)
    assert not os.path.exists(tmpfile)

def test_open_read_write_close():
    filename = str(udir.join('test_open_read_write_close.txt'))
    def does_stuff():
        fd = os.open(filename, os.O_WRONLY | os.O_CREAT, 0777)
        count = os.write(fd, "hello world\n")
        assert count == len("hello world\n")
        os.close(fd)
        fd = os.open(filename, os.O_RDONLY, 0777)
        data = os.read(fd, 500)
        assert data == "hello world\n"
        os.close(fd)

    f1 = compile(does_stuff, [])
    f1()
    assert open(filename, 'r').read() == "hello world\n"
    os.unlink(filename)

def test_getcwd():
    def does_stuff():
        return os.getcwd()
    f1 = compile(does_stuff, [])
    res = f1()
    assert res == os.getcwd()

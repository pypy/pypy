import autopath
from pypy.tool.udir import udir
from pypy.translator.c.test.test_genc import compile


def test_time_clock():
    import time
    def does_stuff():
        return time.clock()
    f1 = compile(does_stuff, [])
    t0 = time.clock()
    t1 = f1()
    assert type(t1) is float
    t2 = time.clock()
    assert t0 <= t1 <= t2


def test_os_open():
    import os
    tmpfile = str(udir.join('test_os_open.txt'))
    def does_stuff():
        fd = os.open(tmpfile, os.O_WRONLY | os.O_CREAT, 0777)
        return fd

    f1 = compile(does_stuff, [])
    fd = f1()
    os.close(fd)
    assert os.path.exists(tmpfile)

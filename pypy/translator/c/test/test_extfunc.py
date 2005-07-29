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

def test_open_read_write_seek_close():
    filename = str(udir.join('test_open_read_write_close.txt'))
    def does_stuff():
        fd = os.open(filename, os.O_WRONLY | os.O_CREAT, 0777)
        count = os.write(fd, "hello world\n")
        assert count == len("hello world\n")
        os.close(fd)
        fd = os.open(filename, os.O_RDONLY, 0777)
        result = os.lseek(fd, 1, 0)
        assert result == 1
        data = os.read(fd, 500)
        assert data == "ello world\n"
        os.close(fd)

    f1 = compile(does_stuff, [])
    f1()
    assert open(filename, 'r').read() == "hello world\n"
    os.unlink(filename)

def test_os_stat():
    filename = str(py.magic.autopath())
    def call_stat():
        st = os.stat(filename)
        return st
    f = compile(call_stat, [])
    result = f()
    assert result[0] == os.stat(filename)[0]
    assert result[1] == os.stat(filename)[1]
    assert result[2] == os.stat(filename)[2]

def test_os_fstat():
    if os.environ.get('PYPY_CC', '').startswith('tcc'):
        py.test.skip("segfault with tcc :-(")
    filename = str(py.magic.autopath())
    def call_fstat():
        fd = os.open(filename, os.O_RDONLY, 0777)
        st = os.fstat(fd)
        os.close(fd)
        return st
    f = compile(call_fstat, [])
    result = f()
    assert result[0] == os.stat(filename)[0]
    assert result[1] == os.stat(filename)[1]
    assert result[2] == os.stat(filename)[2]

def test_os_isatty():
    def call_isatty(fd):
        return os.isatty(fd)
    f = compile(call_isatty, [int])
    assert f(0) == os.isatty(0)
    assert f(1) == os.isatty(1)
    assert f(2) == os.isatty(2)

def test_getcwd():
    def does_stuff():
        return os.getcwd()
    f1 = compile(does_stuff, [])
    res = f1()
    assert res == os.getcwd()

def test_math_frexp():
    from math import frexp
    def fn(x):
        return frexp(x)
    f = compile(fn, [float])
    assert f(10.123) == frexp(10.123)

def test_math_modf():
    from math import modf
    def fn(x):
        return modf(x)
    f = compile(fn, [float])
    assert f(10.123) == modf(10.123)

def test_math_hypot():
    from math import hypot
    def fn(x, y):
        return hypot(x, y)
    f = compile(fn, [float, float])
    assert f(9812.231, 1234) == hypot(9812.231, 1234)

simple_math_functions = [
    'acos', 'asin', 'atan', 'ceil', 'cos', 'cosh', 'exp', 'fabs',
    'floor', 'log', 'log10', 'sin', 'sinh', 'sqrt', 'tan', 'tanh'
    ]

def math_function_test(funcname):
    import random
    import math
    mathfn = getattr(math, funcname)
    print funcname, 
    def fn(x):
        return mathfn(x)
    f = compile(fn, [float])
    for x in [0.12334, 0.3, 0.5, 0.9883]:
        print x
        assert f(x) == mathfn(x)

def test_simple_math_functions():
    for funcname in simple_math_functions:
        yield math_function_test, funcname

def test_os_path_exists():
    tmpfile = str(udir.join('test_os_path_exists.TMP'))
    def fn():
        return os.path.exists(tmpfile)
    f = compile(fn, [])
    open(tmpfile, 'w').close()
    assert f() == True
    os.unlink(tmpfile)
    assert f() == False

def test_os_path_isdir():
    directory = "./."
    def fn():
        return os.path.isdir(directory)
    f = compile(fn, [])
    assert f() == True
    directory = "some/random/name"
    def fn():
        return os.path.isdir(directory)
    f = compile(fn, [])
    assert f() == False

def test_time_time():
    import time
    def fn():
        return time.time()
    f = compile(fn, [])
    t0 = time.time()
    res = fn()
    t1 = time.time()
    assert t0 <= res <= t1

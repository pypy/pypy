import autopath
import py
import os, time
from pypy.tool.udir import udir
from pypy.translator.c.test.test_genc import compile
from pypy.translator.c.extfunc import EXTERNALS

def test_all_suggested_primitives():
    for modulename in ['ll_math', 'll_os', 'll_os_path', 'll_time']:
        mod = __import__('pypy.rpython.module.%s' % modulename,
                         None, None, ['__doc__'])
        for func in mod.__dict__.values():
            if getattr(func, 'suggested_primitive', False):
                yield suggested_primitive_implemented, func
def suggested_primitive_implemented(func):
    assert func in EXTERNALS, "missing C implementation for %r" % (func,)

# note: clock synchronizes itself!
def test_time_clock():
    def does_stuff():
        return time.clock()
    f1 = compile(does_stuff, [])
    t0 = time.clock()
    t1 = f1()
    t0 = (t0 + time.clock()) / 2.0
    correct = t0 - t1
    # now we can compare!
    t0 = time.clock()
    t1 = f1() + correct
    assert type(t1) is float
    t2 = time.clock()
    assert t0 <= t1 <= t2

def test_time_sleep():
    def does_nothing():
        time.sleep(0.19)
    f1 = compile(does_nothing, [])
    t0 = time.time()
    f1()
    t1 = time.time()
    assert t0 <= t1
    assert t1 - t0 >= 0.15


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

def test_ftruncate():
    if not hasattr(os, 'ftruncate'):
        py.test.skip("this os has no ftruncate :-(")
    filename = str(udir.join('test_open_read_write_close.txt'))
    def does_stuff():
        fd = os.open(filename, os.O_WRONLY | os.O_CREAT, 0777)
        os.write(fd, "hello world\n")
        os.close(fd)
        fd = os.open(filename, os.O_RDWR, 0777)
        os.ftruncate(fd, 5)
        data = os.read(fd, 500)
        assert data == "hello"
        os.close(fd)
    does_stuff()
    f1 = compile(does_stuff, [])
    f1()
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
    fd = os.open(filename, os.O_RDONLY, 0777)
    def call_fstat(fd):
        st = os.fstat(fd)
        return st
    f = compile(call_fstat, [int])
    osstat = os.stat(filename)
    result = f(fd)
    os.close(fd)
    import stat
    for i in range(len(result)):
        if i == stat.ST_DEV:
            continue # does give 3 instead of 0 for windows
        elif i == stat.ST_ATIME:
            continue # access time will vary
        assert (i, result[i]) == (i, osstat[i])

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

def test_strerror():
    def does_stuff():
        return os.strerror(2)
    f1 = compile(does_stuff, [])
    res = f1()
    assert res == os.strerror(2)

def test_math_pow():
    import math
    def fn(x, y):
        return math.pow(x, y)
    f = compile(fn, [float, float])
    assert f(2.0, 3.0) == math.pow(2.0, 3.0)
    assert f(3.0, 2.0) == math.pow(3.0, 2.0)
    assert f(2.3, 0.0) == math.pow(2.3, 0.0)
    assert f(2.3, -1.0) == math.pow(2.3, -1.0)
    assert f(2.3, -2.0) == math.pow(2.3, -2.0)
    assert f(2.3, 0.5) == math.pow(2.3, 0.5)
    assert f(4.0, 0.5) == math.pow(4.0, 0.5)    

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
        assert (funcname, f(x)) == (funcname, mathfn(x))

def test_simple_math_functions():
    for funcname in simple_math_functions:
        yield math_function_test, funcname

def test_math_errors():
    import math
    def fn(x):
        return math.log(x)
    f = compile(fn, [float])
    assert f(math.e) == math.log(math.e)
    # this is a platform specific mess
    def check(mathf, f, v):
        try:
            r = mathf(v)
        except (OverflowError, ValueError), e:
            #print mathf, v, e.__class__
            py.test.raises(e.__class__, f, v)
        else:
            if r != r: # nans
                #print mathf, v, "NAN?", r
                u = f(v)
                assert u != u
            else:
                #print mathf, v, r
                u = f(v)
                assert u == r
                
    check(math.log, f, -1.0)
    check(math.log, f, 0.0)

    def fmod1_0(y):
        return math.fmod(1.0, y)
    f = compile(fmod1_0, [float])
    check(fmod1_0, f, 0.0)

    
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


def test_rarith_parts_to_float():
    from pypy.rpython.rarithmetic import parts_to_float
    def fn(sign, beforept, afterpt, exponent):
        return parts_to_float(sign, beforept, afterpt, exponent)

    f = compile(fn, [str, str, str, str])
    
    data = [
    (("","1","","")     , 1.0),
    (("-","1","","")    , -1.0),
    (("-","1","5","")   , -1.5),
    (("-","1","5","2")  , -1.5e2),
    (("-","1","5","+2") , -1.5e2),
    (("-","1","5","-2") , -1.5e-2),
    ]

    for parts, val in data:
        assert f(*parts) == val

def test_rarith_formatd():
    from pypy.rpython.rarithmetic import formatd
    def fn(x):
        return formatd("%.2f", x)

    f = compile(fn, [float])

    assert f(0.0) == "0.00"
    assert f(1.5) == "1.50"
    assert f(2.0) == "2.00"

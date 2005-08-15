from __future__ import division

import sys
import os
import py

from pypy.tool.udir import udir
from pypy.translator.llvm2.genllvm import compile_function

py.log.setconsumer("genllvm", py.log.STDOUT)
py.log.setconsumer("genllvm database prepare", None)

def test_external_function_ll_os_dup():
    def fn():
        return os.dup(0)
    f = compile_function(fn, [])
    assert os.path.sameopenfile(f(), fn())

def test_external_function_ll_time_time():
    import time
    def fn():
        return time.time()
    f = compile_function(fn, [])
    assert abs(f()-fn()) < 10.0

def test_external_function_ll_time_clock():
    import time
    def fn():
        return time.clock()
    f = compile_function(fn, [])
    assert abs(f()-fn()) < 10.0

def test_external_function_ll_time_sleep():
    import time
    def fn(t):
        time.sleep(t)
        return 666
    f = compile_function(fn, [float])
    start_time = time.time()
    delay_time = 2.0
    d = f(delay_time)
    duration = time.time() - start_time
    assert duration >= delay_time - 0.5
    assert duration <= delay_time + 0.5

path = str(udir.join("e"))

def test_os_file_ops_open_close(): 
    def openclose(): 
        fd = os.open(path, os.O_CREAT|os.O_RDWR, 0777) 
        os.close(fd)
        return fd 

    if os.path.exists(path):
        os.unlink(path)
    f = compile_function(openclose, [])
    result = f()
    assert os.path.exists(path)

def test_os_file_ops_open_write_close(): 
    def openwriteclose(): 
        fd = os.open(path, os.O_CREAT|os.O_RDWR, 0777) 
        byteswritten = os.write(fd, path)
        os.close(fd)
        return byteswritten

    if os.path.exists(path):
        os.unlink(path)
    f = compile_function(openwriteclose, [])
    result = f()
    assert os.path.exists(path)
    assert open(path).read() == path

def test_os_file_ops_open_write_read_close(): 
    def openwriteclose_openreadclose():
        fd = os.open(path, os.O_CREAT|os.O_RDWR, 0777) 
        byteswritten = os.write(fd, path+path+path)
        os.close(fd)

        fd = os.open(path, os.O_RDWR, 0777) 
        maxread = 1000
        r = os.read(fd, maxread)
        os.close(fd)

        return len(r)

    if os.path.exists(path):
        os.unlink(path)
    f = compile_function(openwriteclose_openreadclose, [])
    result = f()
    assert os.path.exists(path)
    assert open(path).read() == path * 3
    assert result is len(path) * 3

# following from translator/c/test/test_extfunc.py Revision: 15320 (jul 29th 2005)

def test_os_stat():
    filename = str(py.magic.autopath())
    def call_stat0():
        st = os.stat(filename)
        return st[0]
    def call_stat1():
        st = os.stat(filename)
        return st[1]
    def call_stat2():
        st = os.stat(filename)
        return st[2]
    f0 = compile_function(call_stat0, [])
    f1 = compile_function(call_stat1, [])
    f2 = compile_function(call_stat2, [])
    st = os.stat(filename)
    assert f0() == st[0]
    assert f1() == st[1]
    assert f2() == st[2]

def test_os_fstat():
    filename = str(py.magic.autopath())
    def call_fstat0():
        fd = os.open(filename, os.O_RDONLY, 0777)
        st = os.fstat(fd)
        os.close(fd)
        return st[0]
    def call_fstat1():
        fd = os.open(filename, os.O_RDONLY, 0777)
        st = os.fstat(fd)
        os.close(fd)
        return st[1]
    def call_fstat2():
        fd = os.open(filename, os.O_RDONLY, 0777)
        st = os.fstat(fd)
        os.close(fd)
        return st[2]
    f0 = compile_function(call_fstat0, [])
    f1 = compile_function(call_fstat1, [])
    f2 = compile_function(call_fstat2, [])
    st = os.stat(filename)
    assert f0() == st[0]
    assert f1() == st[1]
    assert f2() == st[2]

def test_getcwd():
    py.test.skip("ll_os_getcwd not implemented")
    def does_stuff():
        return os.getcwd()
    f1 = compile_function(does_stuff, [])
    res = f1()
    assert res == os.getcwd()

def test_math_frexp():
    py.test.skip("ll_math_frexp not implemented")
    from math import frexp
    def fn(x):
        return frexp(x)
    f = compile_function(fn, [float])
    assert f(10.123) == frexp(10.123)

def test_math_modf():
    py.test.skip("ll_math_modf not implemented (next)")
    from math import modf
    def fn(x):
        return modf(x)
    f = compile_function(fn, [float])
    assert f(10.123) == modf(10.123)

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
    f = compile_function(fn, [float])
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
    f = compile_function(fn, [])
    open(tmpfile, 'w').close()
    assert f() == True
    os.unlink(tmpfile)
    assert f() == False

def test_os_path_isdir():
    directory = "./."
    def fn():
        return os.path.isdir(directory)
    f = compile_function(fn, [])
    assert f() == True
    directory = "some/random/name"
    def fn():
        return os.path.isdir(directory)
    f = compile_function(fn, [])
    assert f() == False

def test_os_isatty():
    def call_isatty(fd):
        return os.isatty(fd)
    f = compile_function(call_isatty, [int])
    assert f(0) == os.isatty(0)
    assert f(1) == os.isatty(1)
    assert f(2) == os.isatty(2)

# end of tests taken from c backend

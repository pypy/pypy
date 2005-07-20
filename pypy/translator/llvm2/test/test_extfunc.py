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
    f = compile_function(fn, [], view=False)
    assert abs(f()-fn()) < 10.0

def test_external_function_ll_time_clock():
    import time
    def fn():
        return time.clock()
    f = compile_function(fn, [], view=False)
    assert abs(f()-fn()) < 10.0

def test_external_function_ll_time_sleep():
    import time
    def fn(t):
        time.sleep(t)
        return 666
    f = compile_function(fn, [float], view=False)
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

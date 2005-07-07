from __future__ import division

import sys
import py

from pypy.tool.udir import udir
from pypy.translator.llvm2.genllvm import compile_function

py.log.setconsumer("extfunc", py.log.STDOUT)
py.log.setconsumer("extfunc database prepare", None)

def test_external_function_ll_os_dup():
    import os
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

class TestOSLevelFunctions: 
    def setup_method(self, method): 
        path = udir.join("e")
        self.path = path 
        self.pathints = map(ord, path)
        
def test_os_file_ops_open_close(): 
    # the test is overly complicated because
    # we don't have prebuilt string constants yet 
    import os
    def openclose(a,b,c,d,e,f): 
        s = chr(a) + chr(b) + chr(c) + chr(d) + chr(e) + chr(f)
        fd = os.open(s, os.O_CREAT|os.O_RDWR) 
        os.close(fd)
        return fd 

    path = '/tmp/b'
    if os.path.exists(path):
        os.unlink(path)
    f = compile_function(openclose, [int] * len(path))
    result = f(*map(ord, path))
    assert os.path.exists(path)

def test_os_file_ops_open_write_close(): 
    # the test is overly complicated because
    # we don't have prebuilt string constants yet 
    import os
    def openwriteclose(a,b,c,d,e,f): 
        s = chr(a) + chr(b) + chr(c) + chr(d) + chr(e) + chr(f)
        fd = os.open(s, os.O_CREAT|os.O_RDWR) 
        byteswritten = os.write(fd, s)
        os.close(fd)
        return byteswritten

    path = '/tmp/b'
    if os.path.exists(path):
        os.unlink(path)
    f = compile_function(openwriteclose, [int] * len(path))
    result = f(*map(ord, path))
    assert os.path.exists(path) and open(path).read() == path

def DONTtest_os_file_ops_open_write_read_close(): 
    # the test is overly complicated because
    # we don't have prebuilt string constants yet 
    import os
    def openwriteclose_openreadclose(a,b,c,d,e,f): 
        s = chr(a) + chr(b) + chr(c) + chr(d) + chr(e) + chr(f)

        fd = os.open(s, os.O_CREAT|os.O_RDWR) 
        byteswritten = os.write(fd, s)
        os.close(fd)

        fd = os.open(s, os.os.O_RD) 
        r = os.read(fd, n=1000)
        os.close(fd)

        return r

    path = '/tmp/b'
    if os.path.exists(path):
        os.unlink(path)
    f = compile_function(openwriteclose_openreadclose, [int] * len(path))
    result = f(*map(ord, path))
    assert os.path.exists(path) and open(path).read() is path and result is path

from __future__ import division

import sys
import os
import py

from pypy.tool.udir import udir
from pypy.translator.llvm.test.runtest import compile_function
from pypy.rpython.rarithmetic import r_uint
from pypy.rpython import ros

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

def test_os_getcwd():
    cwd = os.getcwd()
    def does_stuff():
        return os.getcwd() == cwd
    f1 = compile_function(does_stuff, [])
    assert f1()

def test_math_frexp():
    from math import frexp
    def fn(x):
        res = frexp(x)
        return res[0] + float(res[1])
    f = compile_function(fn, [float])
    res = f(10.123)
    assert res == fn(10.123)

def test_math_modf():
    from math import modf
    def fn(x):
        res = modf(x)
        return res[0] + res[1]
    f = compile_function(fn, [float])
    assert f(10.123) == fn(10.123)

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

def test_dynamic_string_null_termination():
    # forces malloc / versus pbc for NUL testing of C string
    tmpfile = str(udir.join('test_os_path_exists.TMP'))
    def fn(l):
        filename = tmpfile[:l]
        return os.path.exists(filename)
    f = compile_function(fn, [r_uint])
    open(tmpfile, 'w').close()
    lfile = len(tmpfile)
    assert f(lfile) == True
    assert f(lfile-2) == False

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
    
def test_rarith_parts_to_float():
    from pypy.rpython.rarithmetic import parts_to_float
    parts = [
     ["" ,"1","" ,""],
     ["-","1","" ,""],
     ["-","1","5",""],
     ["-","1","5","2"],
     ["-","1","5","+2"],
     ["-","1","5","-2"],
    ]
    val = [1.0, -1.0, -1.5, -1.5e2, -1.5e2, -1.5e-2]
    def fn(i):
        sign, beforept, afterpt, exponent = parts[i]
        return parts_to_float(sign, beforept, afterpt, exponent)
    f = compile_function(fn, [int])
    for i, v in enumerate(val):
        assert f(i) == v

def test_rarith_formatd():
    from pypy.rpython.rarithmetic import formatd
    as_float  = [ 0.0  ,  1.5  ,  2.0  ]
    as_string = ["0.00", "1.50", "2.00"]
    def fn(i):
        return formatd("%.2f", as_float[i]) == as_string[i]
    f = compile_function(fn, [int])
    for i, s in enumerate(as_string):
        assert f(i)

def test_os_unlink():
    tmpfile = str(udir.join('test_os_path_exists.TMP'))
    def fn():
        os.unlink(tmpfile)
        return 0
    f = compile_function(fn, [])
    open(tmpfile, 'w').close()
    fn()
    assert not os.path.exists(tmpfile)

def test_chdir():
    path = '..'
    def does_stuff():
        os.chdir(path)
        return 0
    f1 = compile_function(does_stuff, [])
    curdir = os.getcwd()
    try:
        os.chdir()
    except: pass # toplevel
    def does_stuff2():
        os.chdir(curdir)
        return 0
    f1 = compile_function(does_stuff2, [])
    f1()
    assert curdir == os.getcwd()

def test_mkdir_rmdir():
    path = str(udir.join('test_mkdir_rmdir'))
    def does_stuff(delete):
        if delete:
            os.rmdir(path)
        else:
            os.mkdir(path, 0777)
        return 0
    f1 = compile_function(does_stuff, [bool])
    f1(False)
    assert os.path.exists(path) and os.path.isdir(path)
    f1(True)
    assert not os.path.exists(path)

# more from translator/c/test/test_extfunc.py Revision: 19054


def _real_getenv(var):
    cmd = '''%s -c "import os; x=os.environ.get('%s'); print (x is None) and 'F' or ('T'+x)"''' % (
        sys.executable, var)
    g = os.popen(cmd, 'r')
    output = g.read().strip()
    g.close()
    if output == 'F':
        return None
    elif output.startswith('T'):
        return output[1:]
    else:
        raise ValueError, 'probing for env var returned %r' % (output,)

def _real_envkeys():
    cmd = '''%s -c "import os; print os.environ.keys()"''' % sys.executable
    g = os.popen(cmd, 'r')
    output = g.read().strip()
    g.close()
    if output.startswith('[') and output.endswith(']'):
        return eval(output)
    else:
        raise ValueError, 'probing for all env vars returned %r' % (output,)

def test_putenv():
    s = 'abcdefgh=12345678'
    def put():
        ros.putenv(s)
        return 0
    func = compile_function(put, [])
    func()
    assert _real_getenv('abcdefgh') == '12345678'

posix = __import__(os.name)
if hasattr(posix, "unsetenv"):
    def test_unsetenv():
        def unsetenv():
            os.unsetenv("ABCDEF")
            return 0
        f = compile_function(unsetenv, [])
        os.putenv("ABCDEF", "a")
        assert _real_getenv('ABCDEF') == 'a'
        f()
        assert _real_getenv('ABCDEF') is None
        f()
        assert _real_getenv('ABCDEF') is None

def test_opendir_readdir():
    py.test.skip("XXX need to implement opaque types")
    s = str(udir)
    result = []
    def mylistdir():
        dir = ros.opendir(s)
        try:
            while True:
                nextentry = dir.readdir()
                if nextentry is None:
                    break
                result.append(nextentry)
        finally:
            dir.closedir()
        return 0
    func = compile_function(mylistdir, [])
    result = func()
    result = result.split('\x00')
    assert '.' in result
    assert '..' in result
    result.remove('.')
    result.remove('..')
    result.sort()
    compared_with = os.listdir(str(udir))
    compared_with.sort()
    assert result == compared_with

# end of tests taken from c backend




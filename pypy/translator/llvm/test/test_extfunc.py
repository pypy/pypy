from __future__ import division

import os
import sys

import py
from pypy.tool.udir import udir
from pypy.rlib.rarithmetic import r_uint

py.test.skip("Extfunc support in llvm needs refactoring")
# XXX in particular, try to share the tests from c/test/test_extfunc!

from pypy.translator.llvm.test.runtest import *

def test_external_function_ll_os_dup():
    def fn():
        return os.dup(0)
    f = compile_function(fn, [], isolate=False)
    fn()
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
    f = compile_function(fn, [], isolate=False)
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
    if sys.maxint != 2**31-1:
        py.test.skip("WIP on 64 bit architectures") 
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
    if sys.maxint != 2**31-1:
        py.test.skip("WIP on 64 bit architectures") 
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
    if sys.maxint != 2**31-1:
        py.test.skip("WIP on 64 bit architectures") 
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
    if sys.maxint != 2**31-1:
        py.test.skip("WIP on 64 bit architectures") 
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
    if sys.maxint != 2**31-1:
        py.test.skip("WIP on 64 bit architectures") 
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
    if sys.maxint != 2**31-1:
        py.test.skip("WIP on 64 bit architectures") 
    tmpfile = str(udir.join('test_os_path_exists.TMP'))
    def fn():
        return os.path.exists(tmpfile)
    f = compile_function(fn, [])
    open(tmpfile, 'w').close()
    assert f() == True
    os.unlink(tmpfile)
    assert f() == False

def test_dynamic_string_null_termination():
    if sys.maxint != 2**31-1:
        py.test.skip("WIP on 64 bit architectures") 
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
    if sys.maxint != 2**31-1:
        py.test.skip("WIP on 64 bit architectures") 
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
    f = compile_function(call_isatty, [int], isolate=False)
    assert f(0) == os.isatty(0)
    assert f(1) == os.isatty(1)
    assert f(2) == os.isatty(2)
    
def test_rarith_parts_to_float():
    if sys.maxint != 2**31-1:
        py.test.skip("WIP on 64 bit architectures") 
    from pypy.rlib.rarithmetic import parts_to_float
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
    if sys.maxint != 2**31-1:
        py.test.skip("WIP on 64 bit architectures") 
    from pypy.rlib.rarithmetic import formatd
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


def test_lock():
    py.test.skip("XXX does not work with exception transform (why not?)")
    import thread
    import pypy.module.thread.rpython.exttable   # for declare()/declaretype()
    def fn():
        l = thread.allocate_lock()
        ok1 = l.acquire(True)
        ok2 = l.acquire(False)
        l.release()
        ok2_and_a_half = False
        try:
            l.release()
        except thread.error:
            ok2_and_a_half = True
        ok3 = l.acquire(False)
        return ok1 and not ok2 and ok2_and_a_half and ok3
    f = compile_function(fn, [])
    res = f()
    assert res

def test_simple_start_new_thread():
    import thread
    import pypy.module.thread.rpython.exttable   # for declare()/declaretype()
    class Arg:
        pass
    def mythreadedfunction(arg):
        assert arg.value == 42
    def myotherthreadedfunction(arg):
        assert arg.value == 43
    a42 = Arg()
    a42.value = 42
    a43 = Arg()
    a43.value = 43
    def fn(i):
        thread.start_new_thread(mythreadedfunction, (a42,))
        thread.start_new_thread(myotherthreadedfunction, (a43,))
        if i == 1:
            x = mythreadedfunction
            a = a42
        else:
            x = myotherthreadedfunction
            a = a43
        thread.start_new_thread(x, (a,))
        return 42
    f = compile_function(fn, [int])
    res = f(1)
    assert res == 42

def test_start_new_thread():
    if sys.maxint != 2**31-1:
        py.test.skip("WIP on 64 bit architectures") 
    import thread
    import pypy.module.thread.rpython.exttable   # for declare()/declaretype()
    class Arg:
        pass
    a = Arg()
    a.x = 5
    def mythreadedfunction(arg):
        arg.x += 37
        arg.myident = thread.get_ident()
        arg.lock.release()
    def fn():
        a.lock = thread.allocate_lock()
        a.lock.acquire(True)
        ident = thread.start_new_thread(mythreadedfunction, (a,))
        assert ident != thread.get_ident()
        a.lock.acquire(True)  # wait for the thread to finish
        assert a.myident == ident
        return a.x
    f = compile_function(fn, [])
    res = f()
    assert res == 42

def test_prebuilt_lock():
    import thread
    import pypy.module.thread.rpython.exttable   # for declare()/declaretype()
    lock0 = thread.allocate_lock()
    lock1 = thread.allocate_lock()
    lock1.acquire()
    def fn(i):
        lock = [lock0, lock1][i]
        ok = lock.acquire(False)
        if ok: lock.release()
        return ok
    f = compile_function(fn, [int])
    res = f(0)
    assert res == True
    res = f(1)
    assert res == False

def test_pipe_dup_dup2():
    def does_stuff():
        a, b = os.pipe()
        c = os.dup(a)
        d = os.dup(b)
        assert a != b
        assert a != c
        assert a != d
        assert b != c
        assert b != d
        assert c != d
        os.close(c)
        os.dup2(d, c)
        e, f = os.pipe()
        assert e != a
        assert e != b
        assert e != c
        assert e != d
        assert f != a
        assert f != b
        assert f != c
        assert f != d
        assert f != e
        os.close(a)
        os.close(b)
        os.close(c)
        os.close(d)
        os.close(e)
        os.close(f)
        return 42
    f1 = compile_function(does_stuff, [])
    res = f1()
    assert res == 42

def test_os_chmod():
    tmpfile = str(udir.join('test_os_chmod.txt'))
    f = open(tmpfile, 'w')
    f.close()
    def does_stuff(mode):
        os.chmod(tmpfile, mode)
        return 0
    f1 = compile_function(does_stuff, [int])
    f1(0000)
    assert os.stat(tmpfile).st_mode & 0777 == 0000
    f1(0644)
    assert os.stat(tmpfile).st_mode & 0777 == 0644

def test_os_rename():
    tmpfile1 = str(udir.join('test_os_rename_1.txt'))
    tmpfile2 = str(udir.join('test_os_rename_2.txt'))
    f = open(tmpfile1, 'w')
    f.close()
    def does_stuff():
        os.rename(tmpfile1, tmpfile2)
        return 0
    f1 = compile_function(does_stuff, [])
    f1()
    assert os.path.exists(tmpfile2)
    assert not os.path.exists(tmpfile1)

if hasattr(os, 'getpid'):
    def test_os_getpid():
        def does_stuff():
            return os.getpid()
        f1 = compile_function(does_stuff, [], isolate=False)
        res = f1()
        assert res == os.getpid()

if hasattr(os, 'link'):
    def test_links():
        import stat
        tmpfile1 = str(udir.join('test_links_1.txt'))
        tmpfile2 = str(udir.join('test_links_2.txt'))
        tmpfile3 = str(udir.join('test_links_3.txt'))
        f = open(tmpfile1, 'w')
        f.close()
        def does_stuff():
            os.symlink(tmpfile1, tmpfile2)
            os.link(tmpfile1, tmpfile3)
            assert os.readlink(tmpfile2) == tmpfile1
            flag= 0
            st = os.lstat(tmpfile1)
            flag = flag*10 + stat.S_ISREG(st[0])
            flag = flag*10 + stat.S_ISLNK(st[0])
            st = os.lstat(tmpfile2)
            flag = flag*10 + stat.S_ISREG(st[0])
            flag = flag*10 + stat.S_ISLNK(st[0])
            st = os.lstat(tmpfile3)
            flag = flag*10 + stat.S_ISREG(st[0])
            flag = flag*10 + stat.S_ISLNK(st[0])
            return flag
        f1 = compile_function(does_stuff, [])
        res = f1()
        assert res == 100110
        assert os.path.islink(tmpfile2)
        assert not os.path.islink(tmpfile3)
if hasattr(os, 'fork'):
    def test_fork():
        def does_stuff():
            pid = os.fork()
            if pid == 0:   # child
                os._exit(4)
            pid1, status1 = os.waitpid(pid, 0)
            assert pid1 == pid
            return status1
        f1 = compile_function(does_stuff, [])
        status1 = f1()
        assert os.WIFEXITED(status1)
        assert os.WEXITSTATUS(status1) == 4

if hasattr(posix, 'execv'):
    def test_execv():
        py.test.skip("not working yet")
        filename = str(udir.join('test_execv.txt'))
        executable = sys.executable
        def does_stuff():
            progname = str(executable)
            l = ['', '']
            l[0] = progname
            l[1] = "-c"
            l.append('open("%s","w").write("1")' % filename)
            pid = os.fork()
            if pid == 0:
                os.execv(progname, l)
            else:
                os.waitpid(pid, 0)
            return 1
        func = compile_function(does_stuff, [])
        func()
        assert open(filename).read() == "1"

    def test_execv_raising():
        py.test.skip("not working yet")
        def does_stuff():
            l = []
            l.append("asddsadw32eewdfwqdqwdqwd")
            try:
                os.execv(l[0], l)
            except OSError:
                return 1
            else:
                return 0
        func = compile_function(does_stuff, [])
        res = func()
        assert res == 1

    def test_execve():
        py.test.skip("not working yet")
        filename = str(udir.join('test_execve.txt'))
        executable = sys.executable
        def does_stuff():
            progname = executable
            l = []
            l.append(progname)
            l.append("-c")
            l.append('import os; open("%s", "w").write(os.environ["STH"])' % filename)
            env = {}
            env["STH"] = "42"
            env["sthelse"] = "a"
            pid = os.fork()
            if pid == 0:
                os.execve(progname, l, env)
            else:
                os.waitpid(pid, 0)
            return 1
        func = compile_function(does_stuff, [])
        func()
        assert open(filename).read() == "42"

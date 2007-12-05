import os
import sys

import py
from pypy.tool.udir import udir
from pypy.rlib.rarithmetic import r_uint

from pypy.rpython.lltypesystem.lltype import Signed, Ptr, Char, malloc
from pypy.rpython.lltypesystem import lltype

from pypy.translator.llvm.test.runtest import *
from pypy.rpython.lltypesystem import rffi

def test_external_function_ll_os_dup():
    def fn():
        return os.dup(0)
    f = compile_function(fn, [], isolate_hint=False)
    fn()
    assert os.path.sameopenfile(f(), fn())

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
    f = compile_function(call_isatty, [int], isolate_hint=False)
    assert f(0) == os.isatty(0)
    assert f(1) == os.isatty(1)
    assert f(2) == os.isatty(2)
    

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
        f1 = compile_function(does_stuff, [], isolate_hint=False)
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

posix = __import__(os.name)
if hasattr(posix, 'execv'):
    def test_execv():
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

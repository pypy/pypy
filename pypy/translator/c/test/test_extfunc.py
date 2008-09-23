import autopath
import py
import os, time, sys
from pypy.tool.udir import udir
from pypy.rlib.rarithmetic import r_longlong
from pypy.translator.c.test.test_genc import compile
posix = __import__(os.name)

# note: clock synchronizes itself!
def test_time_clock():
    def does_stuff():
        return time.clock()
    f1 = compile(does_stuff, [])
    t0 = time.clock()
    t1 = f1()
    t2 = time.clock()
    t3 = f1()
    t4 = time.clock()
    t5 = f1()
    t6 = time.clock()
    # time.clock() and t1() might have a different notion of zero, so
    # we can only subtract two numbers returned by the same function.
    assert 0 <= t2-t0
    assert 0 <= t3-t1 <= t4-t0
    assert 0 <= t4-t2 <= t5-t1 <= t6-t0
    assert 0 <= t5-t3 <= t6-t2
    assert 0 <= t6-t4

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

def test_big_read():
    filename = str(udir.join('test_open_read_write_close.txt'))
    def does_stuff():
        fd = os.open(filename, os.O_WRONLY | os.O_CREAT, 0777)
        count = os.write(fd, "hello world\n")
        os.close(fd)
        fd = os.open(filename, os.O_RDONLY, 0777)
        data = os.read(fd, 500000)
        os.close(fd)

    f1 = compile(does_stuff, [])
    f1()
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

def test_largefile():
    if not hasattr(os, 'ftruncate'):
        py.test.skip("this os has no ftruncate :-(")
    from pypy.module.posix.test.test_posix2 import need_sparse_files
    need_sparse_files()
    filename = str(udir.join('test_largefile'))
    r4800000000  = r_longlong(4800000000L)
    r4900000000  = r_longlong(4900000000L)
    r5000000000  = r_longlong(5000000000L)
    r5200000000  = r_longlong(5200000000L)
    r9900000000  = r_longlong(9900000000L)
    r10000000000 = r_longlong(10000000000L)
    def does_stuff():
        fd = os.open(filename, os.O_RDWR | os.O_CREAT, 0666)
        os.ftruncate(fd, r10000000000)
        res = os.lseek(fd, r9900000000, 0)
        assert res == r9900000000
        res = os.lseek(fd, -r5000000000, 1)
        assert res == r4900000000
        res = os.lseek(fd, -r5200000000, 2)
        assert res == r4800000000
        os.close(fd)
        st = os.stat(filename)
        assert st.st_size == r10000000000
    does_stuff()
    os.unlink(filename)
    f1 = compile(does_stuff, [])
    f1()
    os.unlink(filename)

def test_os_access():
    filename = str(py.magic.autopath())
    def call_access(path, mode):
        return os.access(path, mode)
    f = compile(call_access, [str, int])
    for mode in os.R_OK, os.W_OK, os.X_OK, (os.R_OK | os.W_OK | os.X_OK):
        assert f(filename, mode) == os.access(filename, mode)


def test_os_stat():
    filename = str(py.magic.autopath())
    has_blksize = hasattr(os.stat_result, 'st_blksize')
    has_blocks = hasattr(os.stat_result, 'st_blocks')
    def call_stat():
        st = os.stat(filename)
        res = (st[0], st.st_ino, st.st_ctime)
        if has_blksize: res += (st.st_blksize,)
        if has_blocks: res += (st.st_blocks,)
        return res
    f = compile(call_stat, [])
    res = f()
    assert res[0] == os.stat(filename).st_mode
    assert res[1] == os.stat(filename).st_ino
    if sys.platform.startswith('win'):
        py.test.skip("in-progress - bogus stat().st_time")
    st_ctime = res[2]
    if isinstance(st_ctime, float):
        assert st_ctime == os.stat(filename).st_ctime
    else:
        assert st_ctime == int(os.stat(filename).st_ctime)
    if has_blksize:
        assert res[3] == os.stat(filename).st_blksize
        if has_blocks:
            assert res[4] == os.stat(filename).st_blocks

def test_os_fstat():
    if os.environ.get('PYPY_CC', '').startswith('tcc'):
        py.test.skip("segfault with tcc :-(")
    filename = str(py.magic.autopath())
    fd = os.open(filename, os.O_RDONLY, 0777)
    def call_fstat(fd):
        st = os.fstat(fd)
        return (st.st_mode, st[1], st.st_mtime)
    f = compile(call_fstat, [int])
    osstat = os.stat(filename)
    st_mode, st_ino, st_mtime = f(fd)
    os.close(fd)
    assert st_mode  == osstat.st_mode
    assert st_ino   == osstat.st_ino
    if sys.platform.startswith('win'):
        py.test.skip("in-progress - bogus stat().st_time")
    if isinstance(st_mtime, float):
        assert st_mtime == osstat.st_mtime
    else:
        assert st_mtime == int(osstat.st_mtime)

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

def test_system():
    def does_stuff(cmd):
        return os.system(cmd)
    f1 = compile(does_stuff, [str])
    res = f1("echo hello")
    assert res == 0

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
    from pypy.rlib.rarithmetic import parts_to_float
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
    from pypy.rlib.rarithmetic import formatd
    def fn(x):
        return formatd("%.2f", x)

    f = compile(fn, [float])

    assert f(0.0) == "0.00"
    assert f(1.5) == "1.50"
    assert f(2.0) == "2.00"

def test_rarith_float_to_str():
    def fn(f):
        return str(f)
    f = compile(fn, [float])
    res = f(1.5)
    assert eval(res) == 1.5

def test_lock():
    py.test.skip("XXX out-of-date, and should not be here")
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
    f = compile(fn, [])
    res = f()
    assert res is True

def test_simple_start_new_thread():
    py.test.skip("XXX out-of-date, and should not be here")
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
    f = compile(fn, [int])
    res = f(1)
    assert res == 42

def test_start_new_thread():
    py.test.skip("XXX out-of-date, and should not be here")
    import thread
    import pypy.module.thread.rpython.exttable   # for declare()/declaretype()
    class Arg:
        pass
    a = Arg()
    a.x = 5
    a.lock = thread.allocate_lock()
    def mythreadedfunction(arg):
        arg.x += 37
        arg.myident = thread.get_ident()
        arg.lock.release()
    def fn():
        a.lock.acquire(True)
        ident = thread.start_new_thread(mythreadedfunction, (a,))
        assert ident != thread.get_ident()
        a.lock.acquire(True)  # wait for the thread to finish
        assert a.myident == ident
        return a.x
    f = compile(fn, [])
    res = f()
    assert res == 42

def test_prebuilt_lock():
    py.test.skip("XXX out-of-date, and should not be here")
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
    f = compile(fn, [int])
    res = f(0)
    assert res is True
    res = f(1)
    assert res is False

def test_os_unlink():
    tmpfile = str(udir.join('test_os_path_exists.TMP'))
    def fn():
        os.unlink(tmpfile)
    f = compile(fn, [])
    open(tmpfile, 'w').close()
    fn()
    assert not os.path.exists(tmpfile)

def test_chdir():
    def does_stuff(path):
        os.chdir(path)
    f1 = compile(does_stuff, [str])
    curdir = os.getcwd()
    try:
        os.chdir('..')
    except: pass # toplevel
    f1(curdir)
    assert curdir == os.getcwd()

def test_mkdir_rmdir():
    def does_stuff(path, delete):
        if delete:
            os.rmdir(path)
        else:
            os.mkdir(path, 0777)
    f1 = compile(does_stuff, [str, bool])
    dirname = str(udir.join('test_mkdir_rmdir'))
    f1(dirname, False)
    assert os.path.exists(dirname) and os.path.isdir(dirname)
    f1(dirname, True)
    assert not os.path.exists(dirname)

def test_strerror():
    def does_stuff(n):
        return os.strerror(n)
    f1 = compile(does_stuff, [int])
    for i in range(4):
        res = f1(i)
        assert res == os.strerror(i)

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
    f1 = compile(does_stuff, [])
    res = f1()
    assert res == 42

def test_os_chmod():
    tmpfile = str(udir.join('test_os_chmod.txt'))
    f = open(tmpfile, 'w')
    f.close()
    # use a witness for the permissions we should expect -
    # on Windows it is not possible to change all the bits with chmod()
    tmpfile2 = str(udir.join('test_os_chmod_witness.txt'))
    f = open(tmpfile2, 'w')
    f.close()
    def does_stuff(mode):
        os.chmod(tmpfile, mode)
    f1 = compile(does_stuff, [int])
    f1(0000)
    os.chmod(tmpfile2, 0000)
    assert os.stat(tmpfile).st_mode & 0777 == os.stat(tmpfile2).st_mode & 0777
    f1(0644)
    os.chmod(tmpfile2, 0644)
    assert os.stat(tmpfile).st_mode & 0777 == os.stat(tmpfile2).st_mode & 0777

def test_os_rename():
    tmpfile1 = str(udir.join('test_os_rename_1.txt'))
    tmpfile2 = str(udir.join('test_os_rename_2.txt'))
    f = open(tmpfile1, 'w')
    f.close()
    def does_stuff():
        os.rename(tmpfile1, tmpfile2)
    f1 = compile(does_stuff, [])
    f1()
    assert os.path.exists(tmpfile2)
    assert not os.path.exists(tmpfile1)

def test_os_umask():
    def does_stuff():
        mask1 = os.umask(0660)
        mask2 = os.umask(mask1)
        return mask2
    f1 = compile(does_stuff, [])
    res = f1()
    assert res == does_stuff()

if hasattr(os, 'getpid'):
    def test_os_getpid():
        def does_stuff():
            return os.getpid()
        f1 = compile(does_stuff, [])
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
        f1 = compile(does_stuff, [])
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
        f1 = compile(does_stuff, [])
        status1 = f1()
        assert os.WIFEXITED(status1)
        assert os.WEXITSTATUS(status1) == 4
    if hasattr(os, 'kill'):
        def test_kill():
            import signal
            def does_stuff():
                pid = os.fork()
                if pid == 0:   # child
                    time.sleep(5)
                    os._exit(4)
                os.kill(pid, signal.SIGTERM)  # in the parent
                pid1, status1 = os.waitpid(pid, 0)
                assert pid1 == pid
                return status1
            f1 = compile(does_stuff, [])
            status1 = f1()
            assert os.WIFSIGNALED(status1)
            assert os.WTERMSIG(status1) == signal.SIGTERM
elif hasattr(os, 'waitpid'):
    # windows has no fork but some waitpid to be emulated
    def test_waitpid():
        prog = str(sys.executable)
        def does_stuff():
            args = [prog]
#            args = [prog, '-c', '"import os;os._exit(4)"']
#           note that the above variant creates a bad array
            args.append('-c')
            args.append('"import os;os._exit(4)"')
            pid = os.spawnv(os.P_NOWAIT, prog, args)
            #if pid == 0:   # child
            #    os._exit(4)
            pid1, status1 = os.waitpid(pid, 0)
            assert pid1 == pid
            return status1
        f1 = compile(does_stuff, [])
        status1 = f1()
        # for what reason do they want us to shift by 8? See the doc
        assert status1 >> 8 == 4

# ____________________________________________________________

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

def test_dictlike_environ_getitem():
    def fn(s):
        try:
            return os.environ[s]
        except KeyError:
            return '--missing--'
    func = compile(fn, [str])
    os.environ.setdefault('USER', 'UNNAMED_USER')
    result = func('USER')
    assert result == os.environ['USER']
    result = func('PYPY_TEST_DICTLIKE_MISSING')
    assert result == '--missing--'

def test_dictlike_environ_get():
    def fn(s):
        res = os.environ.get(s)
        if res is None: res = '--missing--'
        return res
    func = compile(fn, [str])
    os.environ.setdefault('USER', 'UNNAMED_USER')
    result = func('USER')
    assert result == os.environ['USER']
    result = func('PYPY_TEST_DICTLIKE_MISSING')
    assert result == '--missing--'

def test_dictlike_environ_setitem():
    def fn(s, t1, t2, t3, t4, t5):
        os.environ[s] = t1
        os.environ[s] = t2
        os.environ[s] = t3
        os.environ[s] = t4
        os.environ[s] = t5
    func = compile(fn, [str, str, str, str, str, str])
    func('PYPY_TEST_DICTLIKE_ENVIRON', 'a', 'b', 'c', 'FOOBAR', '42',
         expected_extra_mallocs = (2, 3, 4))   # at least two, less than 5
    assert _real_getenv('PYPY_TEST_DICTLIKE_ENVIRON') == '42'

def test_dictlike_environ_delitem():
    def fn(s1, s2, s3, s4, s5):
        for n in range(10):
            os.environ[s1] = 't1'
            os.environ[s2] = 't2'
            os.environ[s3] = 't3'
            os.environ[s4] = 't4'
            os.environ[s5] = 't5'
            del os.environ[s3]
            del os.environ[s1]
            del os.environ[s2]
            del os.environ[s4]
            try:
                del os.environ[s2]
            except KeyError:
                pass
            else:
                raise Exception("should have raised!")
            # os.environ[s5] stays
    func = compile(fn, [str, str, str, str, str])
    if hasattr(__import__(os.name), 'unsetenv'):
        expected_extra_mallocs = range(2, 10)
        # at least 2, less than 10: memory for s1, s2, s3, s4 should be freed
        # (each kept-alive entry counts as two: the RPython string used as
        # key in 'envkeepalive.byname' and the raw-allocated char* as value)
    else:
        expected_extra_mallocs = range(10, 18)
        # at least 10, less than 18: memory for the initial s1, s2, s3, s4
        # should be freed, but replaced by new buffers for empty strings
    func('PYPY_TEST_DICTLIKE_ENVDEL1',
         'PYPY_TEST_DICTLIKE_ENVDEL_X',
         'PYPY_TEST_DICTLIKE_ENVDELFOO',
         'PYPY_TEST_DICTLIKE_ENVDELBAR',
         'PYPY_TEST_DICTLIKE_ENVDEL5',
         expected_extra_mallocs = expected_extra_mallocs)
    assert not _real_getenv('PYPY_TEST_DICTLIKE_ENVDEL1')
    assert not _real_getenv('PYPY_TEST_DICTLIKE_ENVDEL_X')
    assert not _real_getenv('PYPY_TEST_DICTLIKE_ENVDELFOO')
    assert not _real_getenv('PYPY_TEST_DICTLIKE_ENVDELBAR')
    assert _real_getenv('PYPY_TEST_DICTLIKE_ENVDEL5') == 't5'

def test_dictlike_environ_keys():
    def fn():
        return '\x00'.join(os.environ.keys())
    func = compile(fn, [])
    os.environ.setdefault('USER', 'UNNAMED_USER')
    try:
        del os.environ['PYPY_TEST_DICTLIKE_ENVKEYS']
    except:
        pass
    result1 = func().split('\x00')
    os.environ['PYPY_TEST_DICTLIKE_ENVKEYS'] = '42'
    result2 = func().split('\x00')
    assert 'USER' in result1
    assert 'PYPY_TEST_DICTLIKE_ENVKEYS' not in result1
    assert 'USER' in result2
    assert 'PYPY_TEST_DICTLIKE_ENVKEYS' in result2

def test_dictlike_environ_items():
    def fn():
        result = []
        for key, value in os.environ.items():
            result.append('%s/%s' % (key, value))
        return '\x00'.join(result)
    func = compile(fn, [])
    os.environ.setdefault('USER', 'UNNAMED_USER')
    result1 = func().split('\x00')
    os.environ['PYPY_TEST_DICTLIKE_ENVITEMS'] = '783'
    result2 = func().split('\x00')
    assert ('USER/%s' % (os.environ['USER'],)) in result1
    assert 'PYPY_TEST_DICTLIKE_ENVITEMS/783' not in result1
    assert ('USER/%s' % (os.environ['USER'],)) in result2
    assert 'PYPY_TEST_DICTLIKE_ENVITEMS/783' in result2

def test_listdir():
    def mylistdir(s):
        try:
            os.listdir('this/directory/really/cannot/exist')
        except OSError:
            pass
        else:
            raise AssertionError("should have failed!")
        result = os.listdir(s)
        return '/'.join(result)
    func = compile(mylistdir, [str])
    for testdir in [str(udir), os.curdir]:
        result = func(testdir)
        result = result.split('/')
        result.sort()
        compared_with = os.listdir(testdir)
        compared_with.sort()
        assert result == compared_with

if hasattr(posix, 'execv') and hasattr(posix, 'fork'):
    def test_execv():
        progname = str(sys.executable)
        filename = str(udir.join('test_execv.txt'))
        def does_stuff():
            l = [progname, '-c', 'open(%r,"w").write("1")' % filename]
            pid = os.fork()
            if pid == 0:
                os.execv(progname, l)
            else:
                os.waitpid(pid, 0)
        func = compile(does_stuff, [], backendopt=False)
        func()
        assert open(filename).read() == "1"

    def test_execv_raising():
        def does_stuff():
            l = []
            l.append("asddsadw32eewdfwqdqwdqwd")
            os.execv(l[0], l)

        func = compile(does_stuff, [])
        py.test.raises(OSError, "func()")

    def test_execve():
        import py; py.test.skip("in-progress")
        filename = str(udir.join('test_execve.txt'))
        def does_stuff():
            progname = str(sys.executable)
            l = []
            l.append(progname)
            l.append("-c")
            l.append('import os; open(%r, "w").write(os.environ["STH"])' % filename)
            env = {}
            env["STH"] = "42"
            env["sthelse"] = "a"
            pid = os.fork()
            if pid == 0:
                os.execve(progname, l, env)
            else:
                os.waitpid(pid, 0)

        func = compile(does_stuff, [])
        func()
        assert open(filename).read() == "42"

if hasattr(posix, 'spawnv'):
    def test_spawnv():
        filename = str(udir.join('test_spawnv.txt'))
        progname = str(sys.executable)
        scriptpath = udir.join('test_spawnv.py')
        scriptpath.write('f=open(%r,"w")\nf.write("2")\nf.close\n' % filename)
        scriptname = str(scriptpath)
        def does_stuff():
            # argument quoting on Windows is completely ill-defined.
            # don't let yourself be fooled by the idea that if os.spawnv()
            # takes a list of strings, then the receiving program will
            # nicely see these strings as arguments with no further quote
            # processing.  Achieving this is nearly impossible - even
            # CPython doesn't try at all.
            l = [progname, scriptname]
            pid = os.spawnv(os.P_NOWAIT, progname, l)
            os.waitpid(pid, 0)
        func = compile(does_stuff, [])
        func()
        assert open(filename).read() == "2"

def test_utime():
    path = str(udir.ensure("test_utime.txt"))
    from time import time, sleep
    t0 = time()
    sleep(1)

    def does_stuff(flag):
        if flag:
            os.utime(path, None)
        else:
            os.utime(path, (int(t0), int(t0)))

    func = compile(does_stuff, [int])
    func(1)
    assert os.stat(path).st_atime > t0
    func(0)
    assert int(os.stat(path).st_atime) == int(t0)

if hasattr(os, 'uname'):
    def test_os_uname():
        def does_stuff(num):
            tup = os.uname()
            lst = [tup[0], tup[1], tup[2], tup[3], tup[4]]
            return lst[num]
        func = compile(does_stuff, [int])
        for i in range(5):
            res = func(i)
            assert res == os.uname()[i]

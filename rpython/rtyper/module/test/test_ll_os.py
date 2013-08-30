import os

from rpython.tool.udir import udir
from rpython.translator.c.test.test_genc import compile
from rpython.rtyper.module import ll_os
#has side effect of registering functions
from rpython.tool.pytest.expecttest import ExpectTest

from rpython.rtyper import extregistry
import errno
import sys
import py

def getllimpl(fn):
    return extregistry.lookup(fn).lltypeimpl

def test_access():
    filename = str(udir.join('test_access.txt'))
    fd = file(filename, 'w')
    fd.close()

    for mode in os.R_OK, os.W_OK, os.X_OK, os.R_OK | os.W_OK | os.X_OK:
        result = getllimpl(os.access)(filename, mode)
        assert result == os.access(filename, mode)


def test_times():
    """
    posix.times should compile as an RPython function and should return a
    five-tuple giving float-representations (seconds, effectively) of the four
    fields from the underlying struct tms and the return value.
    """
    times = eval(compile(lambda: str(os.times()), ())())
    assert isinstance(times, tuple)
    assert len(times) == 5
    for value in times:
        assert isinstance(value, float)

def test_getlogin():
    if not hasattr(os, 'getlogin'):
        py.test.skip('posix specific function')
    try:
        expected = os.getlogin()
    except OSError, e:
        py.test.skip("the underlying os.getlogin() failed: %s" % e)
    data = getllimpl(os.getlogin)()
    assert data == expected

def test_statvfs():
    if not hasattr(os, 'statvfs'):
        py.test.skip('posix specific function')
    try:
        os.statvfs('.')
    except OSError, e:
        py.test.skip("the underlying os.statvfs() failed: %s" % e)
    getllimpl(os.statvfs)('.')

def test_fstatvfs():
    if not hasattr(os, 'fstatvfs'):
        py.test.skip('posix specific function')
    try:
        os.fstatvfs(0)
    except OSError, e:
        py.test.skip("the underlying os.fstatvfs() failed: %s" % e)
    getllimpl(os.fstatvfs)(0)

def test_utimes():
    if os.name != 'nt':
        py.test.skip('Windows specific feature')
    # Windows support centiseconds
    def f(fname, t1):
        os.utime(fname, (t1, t1))

    fname = udir.join('test_utimes.txt')
    fname.ensure()
    t1 = 1159195039.25
    compile(f, (str, float))(str(fname), t1)
    assert t1 == os.stat(str(fname)).st_mtime

def test__getfullpathname():
    if os.name != 'nt':
        py.test.skip('nt specific function')
    posix = __import__(os.name)
    sysdrv = os.getenv('SystemDrive', 'C:')
    stuff = sysdrv + 'stuff'
    data = getllimpl(posix._getfullpathname)(stuff)
    assert data == posix._getfullpathname(stuff)
    # the most intriguing failure of ntpath.py should not repeat, here:
    assert not data.endswith(stuff)

def test_getcwd():
    data = getllimpl(os.getcwd)()
    assert data == os.getcwd()

def test_chdir():
    def check_special_envvar():
        if sys.platform != 'win32':
            return
        pwd = os.getcwd()
        import ctypes
        buf = ctypes.create_string_buffer(1000)
        len = ctypes.windll.kernel32.GetEnvironmentVariableA('=%c:' % pwd[0], buf, 1000)
        if (len == 0) and "WINGDB_PYTHON" in os.environ:
            # the ctypes call seems not to work in the Wing debugger
            return
        assert str(buf.value).lower() == pwd.lower()
        # ctypes returns the drive letter in uppercase,
        # os.getcwd does not,
        # but there may be uppercase in os.getcwd path

    pwd = os.getcwd()
    try:
        check_special_envvar()
        getllimpl(os.chdir)('..')
        assert os.getcwd() == os.path.dirname(pwd)
        check_special_envvar()
    finally:
        os.chdir(pwd)

def test_mkdir():
    filename = str(udir.join('test_mkdir.dir'))
    getllimpl(os.mkdir)(filename, 0)
    exc = py.test.raises(OSError, getllimpl(os.mkdir), filename, 0)
    assert exc.value.errno == errno.EEXIST
    if sys.platform == 'win32':
        assert exc.type is WindowsError

def test_strerror():
    data = getllimpl(os.strerror)(2)
    assert data == os.strerror(2)

def test_system():
    filename = str(udir.join('test_system.txt'))
    arg = '%s -c "print 1+1" > %s' % (sys.executable, filename)
    data = getllimpl(os.system)(arg)
    assert data == 0
    assert file(filename).read().strip() == '2'
    os.unlink(filename)


EXECVE_ENV = {"foo": "bar", "baz": "quux"}

def test_execve():
    if os.name != 'posix':
        py.test.skip('posix specific function')

    ll_execve = getllimpl(os.execve)

    def run_execve(program, args=None, env=None, do_path_lookup=False):
        if args is None:
            args = [program]
        else:
            args = [program] + args
        if env is None:
            env = {}
        # we cannot directly call ll_execve() because it replaces the
        # current process.
        fd_read, fd_write = os.pipe()
        childpid = os.fork()
        if childpid == 0:
            # in the child
            os.close(fd_read)
            os.dup2(fd_write, 1)     # stdout
            os.close(fd_write)
            if do_path_lookup:
                os.execvp(program, args)
            else:
                ll_execve(program, args, env)
            assert 0, "should not arrive here"
        else:
            # in the parent
            os.close(fd_write)
            child_stdout = []
            while True:
                data = os.read(fd_read, 4096)
                if not data: break     # closed
                child_stdout.append(data)
            pid, status = os.waitpid(childpid, 0)
            os.close(fd_read)
            return status, ''.join(child_stdout)

    # Test exit status and code
    result, child_stdout = run_execve("/usr/bin/which", ["true"], do_path_lookup=True)
    result, child_stdout = run_execve(child_stdout.strip()) # /bin/true or /usr/bin/true
    assert os.WIFEXITED(result)
    assert os.WEXITSTATUS(result) == 0
    result, child_stdout = run_execve("/usr/bin/which", ["false"], do_path_lookup=True)
    result, child_stdout = run_execve(child_stdout.strip()) # /bin/false or /usr/bin/false
    assert os.WIFEXITED(result)
    assert os.WEXITSTATUS(result) == 1

    # Test environment
    result, child_stdout = run_execve("/usr/bin/env", env=EXECVE_ENV)
    assert os.WIFEXITED(result)
    assert os.WEXITSTATUS(result) == 0
    assert dict([line.split('=') for line in child_stdout.splitlines()]) == EXECVE_ENV

    # The following won't actually execute anything, so they don't need
    # a child process helper.

    # If the target does not exist, an OSError should result
    info = py.test.raises(
        OSError, ll_execve, "this/file/is/non/existent", [], {})
    assert info.value.errno == errno.ENOENT

    # If the target is not executable, an OSError should result
    info = py.test.raises(
        OSError, ll_execve, "/etc/passwd", [], {})
    assert info.value.errno == errno.EACCES

def test_os_write():
    #Same as test in rpython/test/test_rbuiltin
    fname = str(udir.join('os_test.txt'))
    fd = os.open(fname, os.O_WRONLY|os.O_CREAT, 0777)
    assert fd >= 0
    f = getllimpl(os.write)
    f(fd, 'Hello world')
    os.close(fd)
    with open(fname) as fid:
        assert fid.read() == "Hello world"
    fd = os.open(fname, os.O_WRONLY|os.O_CREAT, 0777)
    os.close(fd)
    py.test.raises(OSError, f, fd, 'Hello world')

def test_os_close():
    fname = str(udir.join('os_test.txt'))
    fd = os.open(fname, os.O_WRONLY|os.O_CREAT, 0777)
    assert fd >= 0
    os.write(fd, 'Hello world')
    f = getllimpl(os.close)
    f(fd)
    py.test.raises(OSError, f, fd)

def test_os_lseek():
    fname = str(udir.join('os_test.txt'))
    fd = os.open(fname, os.O_RDWR|os.O_CREAT, 0777)
    assert fd >= 0
    os.write(fd, 'Hello world')
    f = getllimpl(os.lseek)
    f(fd,0,0)
    assert os.read(fd, 11) == 'Hello world'
    os.close(fd)
    py.test.raises(OSError, f, fd, 0, 0)

def test_os_fsync():
    fname = str(udir.join('os_test.txt'))
    fd = os.open(fname, os.O_WRONLY|os.O_CREAT, 0777)
    assert fd >= 0
    os.write(fd, 'Hello world')
    f = getllimpl(os.fsync)
    f(fd)
    os.close(fd)
    fid = open(fname)
    assert fid.read() == 'Hello world'
    fid.close()
    py.test.raises(OSError, f, fd)

def test_os_fdatasync():
    try:
        f = getllimpl(os.fdatasync)
    except:
        py.test.skip('No fdatasync in os')
    fname = str(udir.join('os_test.txt'))
    fd = os.open(fname, os.O_WRONLY|os.O_CREAT, 0777)
    assert fd >= 0
    os.write(fd, 'Hello world')
    f(fd)
    fid = open(fname)
    assert fid.read() == 'Hello world'
    os.close(fd)
    py.test.raises(OSError, f, fd)


def test_os_kill():
    if not hasattr(os,'kill') or sys.platform == 'win32':
        py.test.skip('No kill in os')
    f = getllimpl(os.kill)
    import subprocess
    import signal
    proc = subprocess.Popen([sys.executable, "-c",
                         "import time;"
                         "time.sleep(10)",
                         ],
                        )
    f(proc.pid, signal.SIGTERM)
    expected = -signal.SIGTERM
    assert proc.wait() == expected

def test_isatty():
    try:
        f = getllimpl(os.isatty)
    except:
        py.test.skip('No isatty in os')
    assert f(-1)  == False


class TestOsExpect(ExpectTest):
    def setup_class(cls):
        if not hasattr(os, 'ttyname'):
            py.test.skip("no ttyname")

    def test_ttyname(self):
        def f():
            import os
            from rpython.rtyper.test.test_llinterp import interpret

            def ll_to_string(s):
                return ''.join(s.chars)

            def f(num):
                try:
                    return os.ttyname(num)
                except OSError:
                    return ''

            assert ll_to_string(interpret(f, [0])) == f(0)
            assert ll_to_string(interpret(f, [338])) == ''

        self.run_test(f)

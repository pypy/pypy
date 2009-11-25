import os
from py.path import local

import pypy
from pypy.tool.udir import udir
from pypy.translator.c.test.test_genc import compile

from pypy.rpython import extregistry
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
    times = compile(lambda: os.times(), ())()
    assert isinstance(times, tuple)
    assert len(times) == 5
    for value in times:
        assert isinstance(value, float)

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



class ExpectTestOs:
    def setup_class(cls):
        if not hasattr(os, 'ttyname'):
            py.test.skip("no ttyname")
    
    def test_ttyname(self):
        import os
        import py
        from pypy.rpython.test.test_llinterp import interpret

        def ll_to_string(s):
            return ''.join(s.chars)
        
        def f(num):
            try:
                return os.ttyname(num)
            except OSError:
                return ''

        assert ll_to_string(interpret(f, [0])) == f(0)
        assert ll_to_string(interpret(f, [338])) == ''

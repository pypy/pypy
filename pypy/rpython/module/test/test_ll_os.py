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
    arg = 'python -c "print 1+1" > %s' % filename
    data = getllimpl(os.system)(arg)
    assert data == 0
    assert file(filename).read().strip() == '2'
    os.unlink(filename)


EXECVE_ENV = {"foo": "bar", "baz": "quux"}
execve_tests = str(local(__file__).dirpath().join('execve_tests.py'))

def test_execve():
    if os.name != 'posix':
        py.test.skip('posix specific function')
    base = " ".join([
        sys.executable,
       execve_tests,
       str(local(pypy.__file__).join('..', '..')),
       ''])

    # Test exit status and code
    result = os.system(base + "execve_true")
    assert os.WIFEXITED(result)
    assert os.WEXITSTATUS(result) == 0
    result = os.system(base + "execve_false")
    assert os.WIFEXITED(result)
    assert os.WEXITSTATUS(result) == 1

    # Test environment
    result = os.popen(base + "execve_env").read()
    assert dict([line.split('=') for line in result.splitlines()]) == EXECVE_ENV

    # These won't actually execute anything, so they don't need a child process
    # helper.
    execve = getllimpl(os.execve)

    # If the target does not exist, an OSError should result
    info = py.test.raises(
        OSError, execve, execve_tests + "-non-existent", [], {})
    assert info.value.errno == errno.ENOENT

    # If the target is not executable, an OSError should result
    info = py.test.raises(
        OSError, execve, execve_tests, [], {})
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

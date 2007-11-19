import os
from pypy.tool.udir import udir
from pypy.translator.c.test.test_genc import compile

from pypy.rpython import extregistry
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

class ExpectTestOs:
    def setup_class(cls):
        if not hasattr(os, 'ttyname'):
            py.test.skip("no ttyname")
        #py.test.skip("XXX get_errno() does not work with ll2ctypes")
    
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

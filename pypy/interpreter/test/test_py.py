
import pypy.interpreter.py
from pypy.tool.udir import udir
import py
import sys

pypath = str(py.path.local(pypy.interpreter.py.__file__).new(basename='py.py'))

def test_executable():
    """Ensures sys.executable points to the py.py script"""
    # TODO : watch out for spaces/special chars in pypath
    output = py.process.cmdexec( '''"%s" -c 'import sys;print sys.executable' ''' % pypath )
    assert output.splitlines()[-1] == pypath

def test_prefix():
    """Make sure py.py sys.prefix and exec_prefix are the same as C Python's"""
    output = py.process.cmdexec( '''"%s" -c 'import sys;print sys.prefix' ''' % pypath )
    assert output.splitlines()[-1] == sys.prefix
    output = py.process.cmdexec( '''"%s" -c 'import sys;print sys.exec_prefix' ''' % pypath )
    assert output.splitlines()[-1] == sys.exec_prefix

def test_argv_command():
    """Some tests on argv"""
    # test 1 : no arguments
    output = py.process.cmdexec( '''"%s" -c 'import sys;print sys.argv' ''' % pypath )
    assert output.splitlines()[-1] == str(['-c'])

    # test 2 : some arguments after
    output = py.process.cmdexec( '''"%s" -c 'import sys;print sys.argv' hello''' % pypath )
    assert output.splitlines()[-1] == str(['-c','hello'])
    
    # test 3 : additionnal pypy parameters
    output = py.process.cmdexec( '''"%s" -O -c 'import sys;print sys.argv' hello''' % pypath )
    assert output.splitlines()[-1] == str(['-c','hello'])

SCRIPT_1 = """
import sys
print sys.argv
"""
def test_scripts():
    tmpfilepath = str(udir.join("test_py_script.py"))
    tmpfile = file( tmpfilepath, "w" )
    tmpfile.write(SCRIPT_1)
    tmpfile.close()

    # test 1 : no arguments
    output = py.process.cmdexec( '''"%s" "%s" ''' % (pypath,tmpfilepath) )
    assert output.splitlines()[-1] == str([tmpfilepath])
    
    # test 2 : some arguments after
    output = py.process.cmdexec( '''"%s" "%s" hello''' % (pypath,tmpfilepath) )
    assert output.splitlines()[-1] == str([tmpfilepath,'hello'])
    
    # test 3 : additionnal pypy parameters
    output = py.process.cmdexec( '''"%s" -O "%s" hello''' % (pypath,tmpfilepath) )
    assert output.splitlines()[-1] == str([tmpfilepath,'hello'])
    

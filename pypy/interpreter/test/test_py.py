
import pypy.interpreter.py
from pypy.tool.udir import udir
import py
import sys

pypath = str(py.path.local(pypy.interpreter.py.__file__).new(basename='py.py'))

def test_executable():
    """Ensures sys.executable points to the py.py script"""
    # TODO : watch out for spaces/special chars in pypath
    output = py.process.cmdexec( '''"%s" "%s" -c "import sys;print sys.executable" ''' %
                                 (sys.executable, pypath) )
    assert output.splitlines()[-1] == pypath

def test_prefix():
    """Make sure py.py sys.prefix and exec_prefix are the same as C Python's"""
    output = py.process.cmdexec( '''"%s" "%s" -c "import sys;print sys.prefix" ''' %
                                 (sys.executable, pypath) )
    assert output.splitlines()[-1] == sys.prefix
    output = py.process.cmdexec( '''"%s" "%s" -c "import sys;print sys.exec_prefix" ''' %
                                 (sys.executable, pypath) )
    assert output.splitlines()[-1] == sys.exec_prefix

def test_argv_command():
    """Some tests on argv"""
    # test 1 : no arguments
    output = py.process.cmdexec( '''"%s" "%s" -c "import sys;print sys.argv" ''' %
                                 (sys.executable, pypath) )
    assert output.splitlines()[-1] == str(['-c'])

    # test 2 : some arguments after
    output = py.process.cmdexec( '''"%s" "%s" -c "import sys;print sys.argv" hello''' %
                                 (sys.executable, pypath) )
    assert output.splitlines()[-1] == str(['-c','hello'])
    
    # test 3 : additionnal pypy parameters
    output = py.process.cmdexec( '''"%s" "%s" -O -c "import sys;print sys.argv" hello''' %
                                 (sys.executable, pypath) )
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
    output = py.process.cmdexec( '''"%s" "%s" "%s" ''' %
                                 (sys.executable, pypath, tmpfilepath) )
    assert output.splitlines()[-1] == str([tmpfilepath])
    
    # test 2 : some arguments after
    output = py.process.cmdexec( '''"%s" "%s" "%s" hello''' %
                                 (sys.executable, pypath, tmpfilepath) )
    assert output.splitlines()[-1] == str([tmpfilepath,'hello'])
    
    # test 3 : additionnal pypy parameters
    output = py.process.cmdexec( '''"%s" "%s" -O "%s" hello''' %
                                 (sys.executable, pypath, tmpfilepath) )
    assert output.splitlines()[-1] == str([tmpfilepath,'hello'])
    

TB_NORMALIZATION_CHK= """
class K(object):
  def __repr__(self):
     return "<normalized>"
  def __str__(self):
     return "-not normalized-"

{}[K()]
"""

def test_tb_normalization():
    tmpfilepath = str(udir.join("test_py_script.py"))
    tmpfile = file( tmpfilepath, "w" )
    tmpfile.write(TB_NORMALIZATION_CHK)
    tmpfile.close()

    e = None
    try:
        output = py.process.cmdexec( '''"%s" "%s" "%s" ''' %
                                     (sys.executable, pypath, tmpfilepath) )
    except py.process.cmdexec.Error, e:
        pass
    assert e," expected failure"
    assert e.err.splitlines()[-1] == 'KeyError: <normalized>'

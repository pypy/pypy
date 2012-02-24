
from pypy.tool.udir import udir
import py
import sys
import pypy
import subprocess

pypypath = py.path.local(pypy.__file__).dirpath("bin", "py.py")

def run(*args):
    argslist = map(str, args)
    popen = subprocess.Popen(argslist, stdout=subprocess.PIPE)
    stdout, stderr = popen.communicate()
    return stdout


def test_executable():
    """Ensures sys.executable points to the py.py script"""
    # TODO : watch out for spaces/special chars in pypypath
    output = run(sys.executable, pypypath, '-S',
                 "-c", "import sys;print sys.executable")
    assert output.splitlines()[-1] == pypypath

def test_special_names():
    """Test the __name__ and __file__ special global names"""
    cmd = "print __name__; print '__file__' in globals()"
    output = run(sys.executable, pypypath, '-S', '-c', cmd)
    assert output.splitlines()[-2] == '__main__'
    assert output.splitlines()[-1] == 'False'

    tmpfilepath = str(udir.join("test_py_script_1.py"))
    tmpfile = file( tmpfilepath, "w" )
    tmpfile.write("print __name__; print __file__\n")
    tmpfile.close()

    output = run(sys.executable, pypypath, '-S', tmpfilepath)
    assert output.splitlines()[-2] == '__main__'
    assert output.splitlines()[-1] == str(tmpfilepath)

def test_argv_command():
    """Some tests on argv"""
    # test 1 : no arguments
    output = run(sys.executable, pypypath, '-S',
                 "-c", "import sys;print sys.argv")
    assert output.splitlines()[-1] == str(['-c'])

    # test 2 : some arguments after
    output = run(sys.executable, pypypath, '-S',
                 "-c", "import sys;print sys.argv", "hello")
    assert output.splitlines()[-1] == str(['-c','hello'])
    
    # test 3 : additionnal pypy parameters
    output = run(sys.executable, pypypath, '-S',
                 "-O", "-c", "import sys;print sys.argv", "hello")
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
    output = run(sys.executable, pypypath, '-S', tmpfilepath)
    assert output.splitlines()[-1] == str([tmpfilepath])
    
    # test 2 : some arguments after
    output = run(sys.executable, pypypath, '-S', tmpfilepath, "hello")
    assert output.splitlines()[-1] == str([tmpfilepath,'hello'])
    
    # test 3 : additionnal pypy parameters
    output = run(sys.executable, pypypath, '-S', "-O", tmpfilepath, "hello")
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
    if sys.platform == "win32":
        py.test.skip("cannot detect process exit code for now")
    tmpfilepath = str(udir.join("test_py_script.py"))
    tmpfile = file( tmpfilepath, "w" )
    tmpfile.write(TB_NORMALIZATION_CHK)
    tmpfile.close()

    popen = subprocess.Popen([sys.executable, str(pypypath), tmpfilepath],
                             stderr=subprocess.PIPE)
    _, stderr = popen.communicate()
    assert stderr.endswith('KeyError: <normalized>\n')

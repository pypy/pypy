import autopath 
import py
import pypy
from pypy.tool import lib_pypy

pypydir = py.path.local(pypy.__file__).dirpath()
distdir = pypydir.dirpath()
testresultdir = distdir.join('testresult') 
assert pypydir.check(dir=1) 
libpythondir = lib_pypy.LIB_PYTHON
regrtestdir = lib_pypy.LIB_PYTHON_VANILLA.join('test') 
modregrtestdir = lib_pypy.LIB_PYTHON_MODIFIED.join('test') 

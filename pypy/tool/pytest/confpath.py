import autopath 
import py
import pypy
from pypy.module.sys.version import CPYTHON_VERSION_DIR

pypydir = py.path.local(pypy.__file__).dirpath()
distdir = pypydir.dirpath()
testresultdir = distdir.join('testresult') 
assert pypydir.check(dir=1) 
libpythondir = distdir.join('lib-python') 
regrtestdir = libpythondir.join(CPYTHON_VERSION_DIR, 'test') 
modregrtestdir = libpythondir.join('modified-' + CPYTHON_VERSION_DIR, 'test') 

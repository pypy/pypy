import autopath 
import py
import pypy

pypydir = py.path.local(pypy.__file__).dirpath()
distdir = pypydir.dirpath()
testresultdir = distdir.join('testresult') 
assert pypydir.check(dir=1) 
libpythondir = distdir.join('lib-python') 
regrtestdir = libpythondir.join('2.4.1', 'test') 
modregrtestdir = libpythondir.join('modified-2.4.1', 'test') 

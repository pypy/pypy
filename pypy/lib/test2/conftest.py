import autopath 
import py
import pypy
from pypy.conftest import gettestobjspace 

lib = py.path.local(pypy.__file__).dirpath()
lib = lib.dirpath('lib-python-2.3.4', 'test')
assert lib.check(dir=1) 
conftest = lib.join('conftest.py').getpymodule() 

def Module(fspath): 
    return conftest.Module(fspath) 

class Directory(conftest.Directory): 
    def __iter__(self): 
        return iter([])


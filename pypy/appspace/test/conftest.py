from __future__ import generators 

import py 
from pypy.conftest import getobjspace, PyPyItem
from pypy.interpreter.main import run_string

class Directory(py.test.collect.Directory): 
    def __iter__(self): 
        return iter([]) 

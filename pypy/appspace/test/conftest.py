from __future__ import generators 

import py 
from pypy.conftest import getobjspace, PyPyItem
from pypy.interpreter.main import run_string

class Directory(py.test.collect.Directory): 
    def __iter__(self): 
        for path in self.fspath.listdir(): 
            if path.check(fnmatch='cpy_test_*.py', file=1): 
                continue 
                #XXX yield RunFileAtAppLevelItem(py.path.extpy(path)) 
            elif self.fil(path): 
                if path.basename in ('test_complexobject.py',): 
                    continue
                yield self.Module(path) 
            elif self.rec(path): 
                yield self.Directory(path) 

class RunFileAtAppLevelItem(PyPyItem): 
    def run(self, driver): 
        space = getobjspace() 
        source = self.extpy.root.read()
        #self.execute_appex(space, run_string, source, str(self.extpy.root), space) 
        run_string(source, str(self.extpy.root), space) 

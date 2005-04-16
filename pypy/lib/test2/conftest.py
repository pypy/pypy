import autopath 
import sys
import py
import pypy
from pypy.conftest import gettestobjspace, option

ModuleType = type(sys)

def make_cpy_module(dottedname, filepath, force=False): 
    try:
        if force: 
            raise KeyError 
        return sys.modules[dottedname]
    except KeyError: 
        mod = ModuleType(dottedname)
        execfile(str(filepath), mod.__dict__)
        sys.modules[dottedname] = mod
        return mod    

libtest = py.path.local(pypy.__file__).dirpath()
libtest = libtest.dirpath('lib-python-2.3.4', 'test')
conftest = libtest.join('conftest.py').pyimport()

def Module(fspath, parent=None): 
    if option.allpypy: 
        return conftest.Module(fspath, parent=parent) 
    return UnittestModuleOnCPython(fspath, parent=parent) 

class Directory(conftest.Directory): 
    def run(self): 
        return []

class UnittestModuleOnCPython(py.test.collect.Module): 
    def _prepare(self): 
        mod = make_cpy_module('unittest', libtest.join('pypy_unittest.py'), force=True) 
        sys.modules['unittest'] = mod 
        mod.raises = py.test.raises 
        self.TestCase = mod.TestCase 
       
    def run(self): 
        self._prepare() 
        try: 
            iterable = self._cache 
        except AttributeError: 
            iterable = self._cache = list(self._iter())
        return list(iterable) 

    def _iter(self): 
        name = self.fspath.purebasename 
        mod = make_cpy_module(name, self.fspath) 
        print mod
        tlist = conftest.app_list_testmethods(mod, self.TestCase, [])
        for (setup, teardown, methods) in tlist: 
            for name, method in methods: 
                yield CpyTestCaseMethod(self.fspath, name, method, 
                                        setup, teardown) 

class CpyTestCaseMethod(py.test.Item): 
    def __init__(self, fspath, name, method, setup, teardown): 
        self.name = name  
        extpy = py.path.extpy(fspath, name) 
        super(CpyTestCaseMethod, self).__init__(extpy) 
        self.method = method 
        self.setup = setup 
        self.teardown = teardown 

    def run(self, driver):      
        self.setup() 
        try: 
            self.execute() 
        finally: 
            self.teardown() 

    def execute(self): 
        return self.method() 

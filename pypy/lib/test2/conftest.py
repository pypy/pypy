import autopath 
import sys
import py
import pypy
from pypy.conftest import gettestobjspace, option

ModuleType = type(sys)

def make_cpy_module(dottedname, filepath, force=True): 
    try:
        if force: 
            raise KeyError 
        return sys.modules[dottedname]
    except KeyError: 
        mod = ModuleType(dottedname)
        execfile(str(filepath), mod.__dict__)
        #print "setting sys.modules[%s] = %s" % (dottedname, mod)
        sys.modules[dottedname] = mod
        return mod    

libtest = py.path.local(pypy.__file__).dirpath()
libtest = libtest.dirpath('lib-python-2.3.4', 'test')
libconftest = libtest.join('conftest.py').getpymodule()  # read())

testlist = None 
doctestmodulelist = None

def hack_test_support_cpython(): 
    global testlist, doctestmodulelist 
    if testlist is None: 
        testlist = []
        doctestmodulelist = []
        mod = make_cpy_module('unittest', libtest.join('pypy_unittest.py', force=True))
        mod.raises = py.test.raises 

        def hack_run_unittest(*classes): 
            testlist.extend(list(classes))
        def hack_run_doctest(name, verbose=None): 
            doctestmodulelist.append(name) 
            
        from test import test_support 
        test_support.run_unittest = hack_run_unittest 
        test_support.run_doctest = hack_run_doctest  
    return sys.modules['unittest']

class UTModuleOnCPython(py.test.collect.Module): 
    def __init__(self, fspath, parent): 
        super(UTModuleOnCPython, self).__init__(fspath, parent) 
        mod = hack_test_support_cpython() 
        self.TestCaseClass = getattr(mod, 'TestCase') 
        
        name = self.fspath.purebasename 
        mod = self._obj = make_cpy_module(name, self.fspath, force=True) 

        # hack out the test case classes for this module 
        testlist[:] = []
        mod.test_main() 
        
        self._testcases = [(cls.__name__, cls) for cls in testlist]
        self._testcases.sort() 
       
    def run(self): 
        return [x[0] for x in self._testcases]

    def join(self, name): 
        for x,cls in self._testcases: 
            if x == name: 
                return UTTestCase(name, parent=self, cls=cls) 

class UTTestCaseMethod(py.test.Function): 
    def run(self): 
        method = self.obj
        setup = method.im_self.setUp 
        teardown = method.im_self.tearDown
        setup() 
        try: 
            method() 
        finally: 
            teardown()

class UTTestCaseInstance(py.test.collect.Instance): 
    Function = UTTestCaseMethod 

class UTTestCase(py.test.collect.Class): 
    Instance = UTTestCaseInstance 

    def __init__(self, name, parent, cls): 
        super(UTTestCase, self).__init__(name, parent) 
        self._obj = cls 

TestDecl = libconftest.TestDecl 

testmap = {
    'test_itertools.py' : TestDecl(True, UTModuleOnCPython), 
    'test_sha.py'        : TestDecl(True, UTModuleOnCPython), 
}

class Directory(libconftest.Directory): 
    testmap = testmap 


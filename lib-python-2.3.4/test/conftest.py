import py
import sys
from pypy.interpreter.gateway import app2interp_temp 
from pypy.interpreter.error import OperationError
from pypy.tool import pytestsupport
from pypy.conftest import gettestobjspace, options
from pypy.interpreter.module import Module as PyPyModule 
from pypy.interpreter.main import run_string, run_file

#
# PyPy's command line extra options (these are added 
# to py.test's standard options) 
#
#Option = py.test.Option
#options = ('pypy options', [
#        Option('-o', '--objspace', action="store", default=None, 
#               type="string", dest="objspacename", 
#               help="object space to run tests on."), 
##])

# 
# Interfacing/Integrating with py.test's collection process 
#

mydir = py.magic.autopath().dirpath()

working_unittests = (
'test_urlparse.py',
'test_base64.py',
'test_binop.py',
'test_bisect.py',
'test_call',
'test_codeop.py',
'test_compile.py',
'test_operator.py',
'test_heapq.py',
'test_sys.py',
)

working_outputtests = (
    # well 
)

# sanity check for when the above lists become long
assert len(dict.fromkeys(working_unittests)) == len(working_unittests), (
    "duplicate entry in working_unittests")
assert len(dict.fromkeys(working_outputtests)) == len(working_outputtests), (
    "duplicate entry in working_outputtests")


def make_module(space, dottedname, filepath): 
    #print "making module", dottedname, "from", filepath 
    w_dottedname = space.wrap(dottedname) 
    mod = PyPyModule(space, w_dottedname) 
    w_globals = mod.w_dict 
    w_filename = space.wrap(str(filepath)) 
    space.builtin.execfile(w_filename, w_globals, w_globals) 
    w_mod = space.wrap(mod) 
    w_modules = space.getitem(space.sys.w_dict, space.wrap('modules'))
    space.setitem(w_modules, w_dottedname, w_mod) 
    return w_mod 

class Directory(py.test.collect.Directory): 
    def __iter__(self): 
        for test in self.fspath.listdir('test_*.py'): 
            if test.basename not in working_outputtests and \
               test.basename not in working_unittests: 
                continue 
            yield Module(test) 

def app_list_testmethods(mod, testcaseclass): 
    """ return [(instance.setUp, instance.tearDown, 
                 [instance.testmethod1, ...]), 
                ...]
    """ 
    #print "entering list_testmethods"
    l = []
    for clsname, cls in mod.__dict__.items(): 
        if hasattr(cls, '__bases__') and \
           issubclass(cls, testcaseclass): 
            instance = cls() 
            #print "checking", instance 
            methods = []
            for methodname in dir(cls): 
                if methodname.startswith('test_'): 
                    name = clsname + '.' + methodname 
                    methods.append((name, getattr(instance, methodname)))
            l.append((instance.setUp, instance.tearDown, methods))
    return l 
list_testmethods = app2interp_temp(app_list_testmethods) 
           
def Module(fspath): 
    output = fspath.dirpath('output', fspath.purebasename)
    if output.check(file=1):
        # ok this is an output test 
        return OutputTestItem(fspath, output) 
    content = fspath.read() 
    if content.find('unittest') != -1: 
        # we can try to run ...  
        return UnittestModule(fspath) 
   
class OutputTestItem(py.test.Item): 
    def __init__(self, fspath, output): 
        self.fspath = fspath 
        self.outputpath = output 
        self.extpy = py.path.extpy(fspath) 

    def run(self, driver): 
        space = gettestobjspace('std') 
        try: 
            run_file(str(self.fspath), space=space) 
        except OperationError, e: 
            raise self.Failed(
                excinfo=pytestsupport.AppExceptionInfo(space, e))
        
class UnittestModule(py.test.collect.Module): 
    def __init__(self, fspath): 
        super(UnittestModule, self).__init__(fspath) 
    
    def _prepare(self): 
        if hasattr(self, 'space'): 
            return
        self.space = space = gettestobjspace('std') 
        w_mod = make_module(space, 'unittest', mydir.join('pypy_unittest.py')) 
        self.w_TestCase = space.getattr(w_mod, space.wrap('TestCase'))
        
    def __iter__(self): 
        self._prepare() 
        try: 
            iterable = self._cache 
        except AttributeError: 
            iterable = self._cache = list(self._iterapplevel())
        for x in iterable: 
            yield x

    def _iterapplevel(self): 
        name = self.fspath.purebasename 
        space = self.space 
        w_mod = make_module(space, name, self.fspath) 
        w_tlist = list_testmethods(space, w_mod, self.w_TestCase)
        tlist_w = space.unpackiterable(w_tlist) 
        for item_w in tlist_w: 
            w_setup, w_teardown, w_methods = space.unpacktuple(item_w) 
            methoditems_w = space.unpackiterable(w_methods)
            for w_methoditem in methoditems_w: 
                w_name, w_method = space.unpacktuple(w_methoditem) 
                yield AppTestCaseMethod(self.fspath, space, w_name, w_method, 
                                        w_setup, w_teardown) 

class AppTestCaseMethod(py.test.Item): 
    def __init__(self, fspath, space, w_name, w_method, w_setup, w_teardown): 
        self.space = space 
        name = space.str_w(w_name) 
        extpy = py.path.extpy(fspath, name) 
        super(AppTestCaseMethod, self).__init__(extpy) 
        self.w_method = w_method 
        self.w_setup = w_setup 
        self.w_teardown = w_teardown 

    def run(self, driver):      
        try: 
            self.space.call_function(self.w_setup) 
            try: 
                self.execute() 
            finally: 
                self.space.call_function(self.w_teardown) 
        except OperationError, e: 
            raise self.Failed(
                excinfo=pytestsupport.AppExceptionInfo(self.space, e))

    def execute(self): 
        self.space.call_function(self.w_method)
        

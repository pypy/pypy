import py
from pypy.interpreter.gateway import app2interp_temp 
from pypy.interpreter.error import OperationError
from pypy.objspace.std import StdObjSpace 

#
# PyPy's command line extra options (these are added 
# to py.test's standard options) 
#
Option = py.test.Option
options = ('pypy options', [
        Option('-o', '--objspace', action="store", default=None, 
               type="string", dest="objspacename", 
               help="object space to run tests on."), 
])


def getobjspace(name=None, _spacecache={}): 
    """ helper for instantiating and caching space's for testing. 
    """ 
    if name is None: 
        name = py.test.config.option.objspacename  
        if name is None:
            name = py.std.os.environ.get('OBJSPACE', 'std')
    else:
        optionname = py.test.config.option.objspacename
        if optionname is not None and optionname != name:
            return None
    try:
        return _spacecache[name]
    except KeyError:
        module = __import__("pypy.objspace.%s" % name, None, None, ["Space"])
        Space = module.Space
        return _spacecache.setdefault(name, Space())

# 
# Interfacing/Integrating with py.test's collection process 
#

class Module(py.test.collect.Module): 
    """ we take care of collecting classes both at app level 
        and at interp-level (because we need to stick a space 
        at the class) ourselves. 
    """
    def collect_function(self, extpy): 
        if extpy.check(func=1, basestarts='test_'):
            if extpy.check(genfunc=1): 
                yield IntTestGenerator(extpy) 
            else: 
                yield IntTestFunction(extpy)

    def collect_app_function(self, extpy): 
        if extpy.check(func=1, basestarts='app_test_'):
            assert not extpy.check(genfunc=1), "you must be joking" 
            yield AppTestFunction(extpy)
            
    def collect_class(self, extpy): 
        if extpy.check(class_=1, basestarts="Test"): 
            yield IntClassCollector(extpy) 

    def collect_appclass(self, extpy): 
        if extpy.check(class_=1, basestarts="AppTest"): 
            yield AppClassCollector(extpy) 

def gettestobjspace(name=None):
    space = getobjspace(name)
    if space is None:
        py.test.skip('test requires object space %r' % (name,))
    return space


class AppFrame(py.code.Frame):

    def __init__(self, pyframe):
        self.code = py.code.Code(pyframe.code)
        self.lineno = pyframe.get_last_lineno() - 1
        self.space = pyframe.space
        self.w_globals = pyframe.w_globals
        self.w_locals = pyframe.getdictscope()
        self.f_locals = self.w_locals   # for py.test's recursion detection

    def eval(self, code, **vars):
        space = self.space
        for key, w_value in vars.items():
            space.setitem(self.w_locals, space.wrap(key), w_value)
        return space.eval(code, self.w_globals, self.w_locals)

    def exec_(self, code, **vars):
        space = self.space
        for key, w_value in vars.items():
            space.setitem(self.w_locals, space.wrap(key), w_value)
        space.exec_(code, self.w_globals, self.w_locals)

    def repr(self, w_value):
        return self.space.unwrap(self.space.repr(w_value))

    def is_true(self, w_value):
        return self.space.is_true(w_value)


class AppExceptionInfo(py.code.ExceptionInfo):
    """An ExceptionInfo object representing an app-level exception."""
    exprinfo = None

    def __init__(self, space, operr):
        self.space = space
        self.operr = operr

    def __str__(self):
        return '(app-level) ' + self.operr.errorstr(self.space)

    def __iter__(self):
        tb = self.operr.application_traceback
        while tb is not None:
            yield AppTracebackEntry(tb)
            tb = tb.next

class AppTracebackEntry(py.code.TracebackEntry):
    def __init__(self, tb):
        self.frame = AppFrame(tb.frame)
        self.lineno = tb.lineno - 1


class PyPyItem(py.test.Item):
    # All PyPy test items catch and display OperationErrors specially.
    def execute_in_space(self, space, target, *args):
        try:
            target(*args)
        except OperationError, e:
            raise self.Failed(excinfo=AppExceptionInfo(space, e))

class IntTestFunction(PyPyItem):
    def execute(self, target, *args):
        co = target.func_code
        if 'space' in co.co_varnames[:co.co_argcount]: 
            name = target.func_globals.get('objspacename', None) 
            space = gettestobjspace(name) 
            self.execute_in_space(space, target, space, *args)
        else:
            target(*args)

class AppTestFunction(PyPyItem): 
    def execute(self, target, *args):
        assert not args 
        name = target.func_globals.get('objspacename', None) 
        space = gettestobjspace(name) 
        func = app2interp_temp(target, target.__name__)
        self.execute_in_space(space, target, space)

class IntTestMethod(PyPyItem): 
    def execute(self, target, *args):
        name = target.func_globals.get('objspacename', None) 
        if name is None: 
            name = getattr(target.im_class, 'objspacename', None)
        instance = target.im_self
        instance.space = space = gettestobjspace(name)
        self.execute_in_space(space, target, *args)

class AppTestMethod(PyPyItem): 
    def execute(self, target, *args): 
        assert not args 
        name = target.func_globals.get('objspacename', None) 
        if name is None: 
            name = getattr(target.im_class, 'objspacename', None)
        space = gettestobjspace(name)
        func = app2interp_temp(target.im_func, target.__name__) 
        self.execute_in_space(space, func, space, space.w_None)

class AppClassCollector(py.test.collect.Class): 
    Item = AppTestMethod 

class IntClassCollector(py.test.collect.Class): 
    Item = IntTestMethod 
    

import py
from pypy.interpreter.gateway import app2interp_temp 
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
            name = os.environ.get('OBJSPACE', 'std')
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
    def collect_class(self, extpy): 
        if extpy.check(class_=1, basestarts="Test"): 
            yield IntClassCollector(extpy) 
    def collect_appclass(self, extpy): 
        if extpy.check(class_=1, basestarts="AppTest"): 
            yield AppClassCollector(extpy) 

class IntTestMethod(py.test.Item): 
    def run(self, driver): 
        cls = self.extpy.resolve().im_class 
        space = getobjspace()
        cls.space = space 
        return super(IntTestMethod, self).run(driver) 

class AppTestMethod(py.test.Item): 
    def execute(self, target, *args): 
        func = app2interp_temp(target.im_func, target.__name__) 
        space = getobjspace()
        func(space, space.w_None) 

class AppClassCollector(py.test.collect.Class): 
    Item = AppTestMethod 

class IntClassCollector(py.test.collect.Class): 
    Item = IntTestMethod 
    

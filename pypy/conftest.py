import py, sys
from pypy.interpreter.gateway import app2interp_temp 
from pypy.interpreter.error import OperationError
from pypy.tool.pytest import appsupport 
from inspect import isclass

rootdir = py.magic.autopath().dirpath()

#
# PyPy's command line extra options (these are added 
# to py.test's standard options) 
#
Option = py.test.Config.Option

#class Options: 
#    group = "pypy options" 
#    optionlist = 

def usemodules_callback(option, opt, value, parser):
    parser.values.usemodules.append(value)

option = py.test.Config.addoptions("pypy options", 
        Option('-O', '--objspace', action="store", default=None, 
               type="string", dest="objspace", 
               help="object space to run tests on."),
        Option('--oldstyle', action="store_true",dest="oldstyle", default=False,
               help="enable oldstyle classes as default metaclass"),
        Option('--uselibfile', action="store_true", 
               dest="uselibfile", default=False,
               help="enable our applevel file implementation"),
        Option('--nofaking', action="store_true", 
               dest="nofaking", default=False,
               help="avoid faking of modules and objects completely."),
        Option('--allpypy', action="store_true",dest="allpypy", default=False, 
               help="run everything possible on top of PyPy."),
        Option('--usemodules', action="callback", type="string", metavar="NAME",
               callback=usemodules_callback, default=[],
               help="(mixed) modules to use."),
    )

def getobjspace(name=None, _spacecache={}): 
    """ helper for instantiating and caching space's for testing. 
    """ 
    name = name or option.objspace or 'std' 
    try:
        return _spacecache[name]
    except KeyError:
        assert name in ('std', 'thunk'), name 
        mod = __import__('pypy.objspace.%s' % name, None, None, ['Space'])
        Space = mod.Space
        try: 
            space = Space(uselibfile=option.uselibfile, 
                          nofaking=option.nofaking, 
                          oldstyle=option.oldstyle,
                          usemodules=option.usemodules
                          )
        except KeyboardInterrupt: 
            raise 
        except OperationError, e: 
            # we cannot easily convert w_KeyboardInterrupt to
            # KeyboardInterrupt so we have to jump through hoops 
            try: 
                if e.w_type.name == 'KeyboardInterrupt': 
                    raise KeyboardInterrupt 
            except AttributeError: 
                pass 
            if option.verbose:  
                import traceback 
                traceback.print_exc() 
            py.test.fail("fatal: cannot initialize objspace:  %r" %(Space,))
        _spacecache[name] = space
        space.setitem(space.builtin.w_dict, space.wrap('AssertionError'), 
                      appsupport.build_pytest_assertion(space))
        space.setitem(space.builtin.w_dict, space.wrap('raises'),
                      space.wrap(appsupport.app_raises))
        space.setitem(space.builtin.w_dict, space.wrap('skip'),
                      space.wrap(appsupport.app_skip))
        space.raises_w = appsupport.raises_w.__get__(space)
        space.eq_w = appsupport.eq_w.__get__(space) 
        return space

# 
# Interfacing/Integrating with py.test's collection process 
#

class Module(py.test.collect.Module): 
    """ we take care of collecting classes both at app level 
        and at interp-level (because we need to stick a space 
        at the class) ourselves. 
    """
    def funcnamefilter(self, name): 
        return name.startswith('test_') or name.startswith('app_test_')
    def classnamefilter(self, name): 
        return name.startswith('Test') or name.startswith('AppTest') 

    def setup(self): 
        # stick py.test raise in module globals
        self.obj.raises = py.test.raises 
        super(Module, self).setup() 
        #    if hasattr(mod, 'objspacename'): 
        #        mod.space = getttestobjspace(mod.objspacename)

    def join(self, name): 
        obj = getattr(self.obj, name) 
        if isclass(obj): 
            if name.startswith('AppTest'): 
                return AppClassCollector(name, parent=self) 
            else: 
                return IntClassCollector(name, parent=self) 
        elif hasattr(obj, 'func_code'): 
            if name.startswith('app_test_'): 
                assert not obj.func_code.co_flags & 32, \
                    "generator app level functions? you must be joking" 
                return AppTestFunction(name, parent=self) 
            elif obj.func_code.co_flags & 32: # generator function 
                return self.Generator(name, parent=self) 
            else: 
                return IntTestFunction(name, parent=self) 

def gettestobjspace(name=None):
    space = getobjspace(name)
    if space is None:
        py.test.skip('test requires object space %r' % (name,))
    return space


class PyPyTestFunction(py.test.Function):
    # All PyPy test items catch and display OperationErrors specially.

    def execute_appex(self, space, target, *args):
        try:
            target(*args)
        except OperationError, e:
            if e.match(space, space.w_KeyboardInterrupt): 
                raise KeyboardInterrupt 
            appexcinfo = appsupport.AppExceptionInfo(space, e) 
            if appexcinfo.traceback: 
                raise self.Failed(excinfo=appsupport.AppExceptionInfo(space, e))
            raise 

_pygame_warned = False

class IntTestFunction(PyPyTestFunction):
    def execute(self, target, *args):
        co = target.func_code
        if 'space' in co.co_varnames[:co.co_argcount]: 
            space = gettestobjspace() 
            target(space, *args)  
        else:
            target(*args)
        if 'pygame' in sys.modules:
            global _pygame_warned
            if not _pygame_warned:
                _pygame_warned = True
                py.test.skip("DO NOT FORGET to remove the Pygame invocation "
                             "before checking in :-)")

class AppTestFunction(PyPyTestFunction): 
    def execute(self, target, *args):
        assert not args 
        space = gettestobjspace() 
        func = app2interp_temp(target)
        print "executing", func
        self.execute_appex(space, func, space)

class AppTestMethod(PyPyTestFunction): 

    def setup(self): 
        super(AppTestMethod, self).setup() 
        instance = self.parent.obj 
        w_instance = self.parent.w_instance 
        space = instance.space  
        for name in dir(instance): 
            if name.startswith('w_'): 
                space.setattr(w_instance, space.wrap(name[2:]), 
                              getattr(instance, name)) 

    def execute(self, target, *args): 
        assert not args 
        space = target.im_self.space 
        func = app2interp_temp(target.im_func) 
        w_instance = self.parent.w_instance 
        self.execute_appex(space, func, space, w_instance) 

class IntClassCollector(py.test.collect.Class): 
    Function = IntTestFunction 

    def setup(self): 
        cls = self.obj 
        cls.space = gettestobjspace() 
        super(IntClassCollector, self).setup() 

class AppClassInstance(py.test.collect.Instance): 
    Function = AppTestMethod 

    def setup(self): 
        super(AppClassInstance, self).setup()         
        instance = self.obj 
        space = instance.space 
        w_class = self.parent.w_class 
        self.w_instance = space.call_function(w_class)

class AppClassCollector(IntClassCollector): 
    Instance = AppClassInstance 

    def setup(self): 
        super(AppClassCollector, self).setup()         
        cls = self.obj 
        space = cls.space 
        clsname = cls.__name__ 
        w_class = space.call_function(space.w_type,
                                      space.wrap(clsname),
                                      space.newtuple([]),
                                      space.newdict([]))
        self.w_class = w_class 

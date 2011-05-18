import py, pytest, sys, os, textwrap, types
from pypy.interpreter.gateway import app2interp_temp
from pypy.interpreter.error import OperationError
from pypy.interpreter.function import Method
from pypy.tool.pytest import appsupport
from pypy.tool.option import make_config, make_objspace
from pypy.config.config import ConflictConfigError
from inspect import isclass, getmro
from pypy.tool.udir import udir
from pypy.tool.autopath import pypydir
from pypy.tool import leakfinder

# pytest settings
rsyncdirs = ['.', '../lib-python', '../lib_pypy', '../demo']
rsyncignore = ['_cache']

# PyPy's command line extra options (these are added
# to py.test's standard options)
#
option = None

def pytest_report_header():
    return "pytest-%s from %s" %(pytest.__version__, pytest.__file__)

def pytest_configure(config):
    global option
    option = config.option

def _set_platform(opt, opt_str, value, parser):
    from pypy.config.translationoption import PLATFORMS
    from pypy.translator.platform import set_platform
    if value not in PLATFORMS:
        raise ValueError("%s not in %s" % (value, PLATFORMS))
    set_platform(value, None)

def pytest_addoption(parser):
    group = parser.getgroup("pypy options")
    group.addoption('--view', action="store_true", dest="view", default=False,
           help="view translation tests' flow graphs with Pygame")
    group.addoption('-A', '--runappdirect', action="store_true",
           default=False, dest="runappdirect",
           help="run applevel tests directly on python interpreter (not through PyPy)")
    group.addoption('--direct', action="store_true",
           default=False, dest="rundirect",
           help="run pexpect tests directly")
    group.addoption('-P', '--platform', action="callback", type="string",
           default="host", callback=_set_platform,
           help="set up tests to use specified platform as compile/run target")
    group = parser.getgroup("JIT options")
    group.addoption('--viewloops', action="store_true",
           default=False, dest="viewloops",
           help="show only the compiled loops")

def pytest_sessionstart():
    # have python subprocesses avoid startup customizations by default
    try:
        del os.environ['PYTHONSTARTUP']
    except KeyError:
        pass

def pytest_funcarg__space(request):
    spaceconfig = getattr(request.cls, 'spaceconfig', {})
    return gettestobjspace(**spaceconfig)

_SPACECACHE={}
def gettestobjspace(name=None, **kwds):
    """ helper for instantiating and caching space's for testing.
    """
    try:
        config = make_config(option, objspace=name, **kwds)
    except ConflictConfigError, e:
        # this exception is typically only raised if a module is not available.
        # in this case the test should be skipped
        py.test.skip(str(e))
    key = config.getkey()
    try:
        return _SPACECACHE[key]
    except KeyError:
        if getattr(option, 'runappdirect', None):
            if name not in (None, 'std'):
                myname = getattr(sys, 'pypy_objspaceclass', '')
                if not myname.lower().startswith(name):
                    py.test.skip("cannot runappdirect test: "
                                 "%s objspace required" % (name,))
            return TinyObjSpace(**kwds)
        space = maketestobjspace(config)
        _SPACECACHE[key] = space
        return space

def maketestobjspace(config=None):
    if config is None:
        config = make_config(option)
    try:
        space = make_objspace(config)
    except OperationError, e:
        check_keyboard_interrupt(e)
        if option.verbose:
            import traceback
            traceback.print_exc()
        py.test.fail("fatal: cannot initialize objspace: %r" %
                         (config.objspace.name,))
    space.startup() # Initialize all builtin modules
    space.setitem(space.builtin.w_dict, space.wrap('AssertionError'),
                  appsupport.build_pytest_assertion(space))
    space.setitem(space.builtin.w_dict, space.wrap('raises'),
                  space.wrap(appsupport.app_raises))
    space.setitem(space.builtin.w_dict, space.wrap('skip'),
                  space.wrap(appsupport.app_skip))
    space.raises_w = appsupport.raises_w.__get__(space)
    space.eq_w = appsupport.eq_w.__get__(space)
    return space

class TinyObjSpace(object):
    def __init__(self, **kwds):
        import sys
        info = getattr(sys, 'pypy_translation_info', None)
        for key, value in kwds.iteritems():
            if key == 'usemodules':
                if info is not None:
                    for modname in value:
                        ok = info.get('objspace.usemodules.%s' % modname,
                                      False)
                        if not ok:
                            py.test.skip("cannot runappdirect test: "
                                         "module %r required" % (modname,))
                else:
                    if '__pypy__' in value:
                        py.test.skip("no module __pypy__ on top of CPython")
                continue
            if info is None:
                py.test.skip("cannot runappdirect this test on top of CPython")
            has = info.get(key, None)
            if has != value:
                #print sys.pypy_translation_info
                py.test.skip("cannot runappdirect test: space needs %s = %s, "\
                    "while pypy-c was built with %s" % (key, value, has))

        for name in ('int', 'long', 'str', 'unicode', 'None'):
            setattr(self, 'w_' + name, eval(name))


    def appexec(self, args, body):
        body = body.lstrip()
        assert body.startswith('(')
        src = py.code.Source("def anonymous" + body)
        d = {}
        exec src.compile() in d
        return d['anonymous'](*args)

    def wrap(self, obj):
        return obj

    def unpackiterable(self, itr):
        return list(itr)

    def is_true(self, obj):
        return bool(obj)

    def str_w(self, w_str):
        return w_str

    def newdict(self, module=None):
        return {}

    def newtuple(self, iterable):
        return tuple(iterable)

    def newlist(self, iterable):
        return list(iterable)

    def call_function(self, func, *args, **kwds):
        return func(*args, **kwds)

    def call_method(self, obj, name, *args, **kwds):
        return getattr(obj, name)(*args, **kwds)

    def getattr(self, obj, name):
        return getattr(obj, name)

    def setattr(self, obj, name, value):
        setattr(obj, name, value)

    def getbuiltinmodule(self, name):
        return __import__(name)

    def delslice(self, obj, *args):
        obj.__delslice__(*args)

def translation_test_so_skip_if_appdirect():
    if option.runappdirect:
        py.test.skip("translation test, skipped for appdirect")


class OpErrKeyboardInterrupt(KeyboardInterrupt):
    pass

def check_keyboard_interrupt(e):
    # we cannot easily convert w_KeyboardInterrupt to KeyboardInterrupt
    # in general without a space -- here is an approximation
    try:
        if e.w_type.name == 'KeyboardInterrupt':
            tb = sys.exc_info()[2]
            raise OpErrKeyboardInterrupt, OpErrKeyboardInterrupt(), tb
    except AttributeError:
        pass

#
# Interfacing/Integrating with py.test's collection process
#
#

def ensure_pytest_builtin_helpers(helpers='skip raises'.split()):
    """ hack (py.test.) raises and skip into builtins, needed
        for applevel tests to run directly on cpython but
        apparently earlier on "raises" was already added
        to module's globals.
    """
    import __builtin__
    for helper in helpers:
        if not hasattr(__builtin__, helper):
            setattr(__builtin__, helper, getattr(py.test, helper))

def pytest_sessionstart(session):
    """ before session.main() is called. """
    # stick py.test raise in module globals -- carefully
    ensure_pytest_builtin_helpers()

def pytest_pycollect_makemodule(path, parent):
    return PyPyModule(path, parent)

class PyPyModule(py.test.collect.Module):
    """ we take care of collecting classes both at app level
        and at interp-level (because we need to stick a space
        at the class) ourselves.
    """
    def accept_regular_test(self):
        if self.config.option.runappdirect:
            # only collect regular tests if we are in an 'app_test' directory,
            # or in test_lib_pypy
            names = self.listnames()
            return "app_test" in names or "test_lib_pypy" in names
        else:
            return True

    def funcnamefilter(self, name):
        if name.startswith('test_'):
            return self.accept_regular_test()
        if name.startswith('app_test_'):
            return True
        return False

    def classnamefilter(self, name):
        if name.startswith('Test'):
            return self.accept_regular_test()
        if name.startswith('AppTest'):
            return True
        if name.startswith('ExpectTest'):
            return True
        #XXX todo
        #if name.startswith('AppExpectTest'):
        #    return True
        return False

    def makeitem(self, name, obj):
        if isclass(obj) and self.classnamefilter(name):
            if name.startswith('AppTest'):
                return AppClassCollector(name, parent=self)
            elif name.startswith('ExpectTest'):
                if self.config.option.rundirect:
                    return py.test.collect.Class(name, parent=self)
                return ExpectClassCollector(name, parent=self)
            # XXX todo
            #elif name.startswith('AppExpectTest'):
            #    if option.rundirect:
            #        return AppClassCollector(name, parent=self)
            #    return AppExpectClassCollector(name, parent=self)
            else:
                return IntClassCollector(name, parent=self)

        elif hasattr(obj, 'func_code') and self.funcnamefilter(name):
            if name.startswith('app_test_'):
                assert not obj.func_code.co_flags & 32, \
                    "generator app level functions? you must be joking"
                return AppTestFunction(name, parent=self)
            elif obj.func_code.co_flags & 32: # generator function
                return pytest.Generator(name, parent=self)
            else:
                return IntTestFunction(name, parent=self)

def skip_on_missing_buildoption(**ropts):
    __tracebackhide__ = True
    import sys
    options = getattr(sys, 'pypy_translation_info', None)
    if options is None:
        py.test.skip("not running on translated pypy "
                     "(btw, i would need options: %s)" %
                     (ropts,))
    for opt in ropts:
        if not options.has_key(opt) or options[opt] != ropts[opt]:
            break
    else:
        return
    py.test.skip("need translated pypy with: %s, got %s"
                 %(ropts,options))

class LazyObjSpaceGetter(object):
    def __get__(self, obj, cls=None):
        space = gettestobjspace()
        if cls:
            cls.space = space
        return space


class AppError(Exception):

    def __init__(self, excinfo):
        self.excinfo = excinfo

def pytest_runtest_setup(__multicall__, item):
    if isinstance(item, py.test.collect.Function):
        appclass = item.getparent(PyPyClassCollector)
        if appclass is not None:
            spaceconfig = getattr(appclass.obj, 'spaceconfig', None)
            if spaceconfig:
                appclass.obj.space = gettestobjspace(**spaceconfig)

    __multicall__.execute()

    if isinstance(item, py.test.collect.Function):
        if not getattr(item.obj, 'dont_track_allocations', False):
            leakfinder.start_tracking_allocations()

def pytest_runtest_call(__multicall__, item):
    __multicall__.execute()
    item._success = True

def pytest_runtest_teardown(__multicall__, item):
    __multicall__.execute()

    if isinstance(item, py.test.collect.Function):
        if (not getattr(item.obj, 'dont_track_allocations', False)
            and leakfinder.TRACK_ALLOCATIONS):
            item._pypytest_leaks = leakfinder.stop_tracking_allocations(False)
        else:            # stop_tracking_allocations() already called
            item._pypytest_leaks = None

        # check for leaks, but only if the test passed so far
        if getattr(item, '_success', False) and item._pypytest_leaks:
            raise leakfinder.MallocMismatch(item._pypytest_leaks)

    if 'pygame' in sys.modules:
        assert option.view, ("should not invoke Pygame "
                             "if conftest.option.view is False")

_pygame_imported = False

class IntTestFunction(py.test.collect.Function):
    def __init__(self, *args, **kwargs):
        super(IntTestFunction, self).__init__(*args, **kwargs)
        self.keywords['interplevel'] = True

    def runtest(self):
        try:
            super(IntTestFunction, self).runtest()
        except OperationError, e:
            check_keyboard_interrupt(e)
            raise
        except Exception, e:
            cls = e.__class__
            while cls is not Exception:
                if cls.__name__ == 'DistutilsPlatformError':
                    from distutils.errors import DistutilsPlatformError
                    if isinstance(e, DistutilsPlatformError):
                        py.test.skip('%s: %s' % (e.__class__.__name__, e))
                cls = cls.__bases__[0]
            raise

class AppTestFunction(py.test.collect.Function):
    def __init__(self, *args, **kwargs):
        super(AppTestFunction, self).__init__(*args, **kwargs)
        self.keywords['applevel'] = True

    def _prunetraceback(self, traceback):
        return traceback

    def execute_appex(self, space, target, *args):
        try:
            target(*args)
        except OperationError, e:
            tb = sys.exc_info()[2]
            if e.match(space, space.w_KeyboardInterrupt):
                raise OpErrKeyboardInterrupt, OpErrKeyboardInterrupt(), tb
            appexcinfo = appsupport.AppExceptionInfo(space, e)
            if appexcinfo.traceback:
                raise AppError, AppError(appexcinfo), tb
            raise

    def runtest(self):
        target = self.obj
        if self.config.option.runappdirect:
            return target()
        space = gettestobjspace()
        filename = self._getdynfilename(target)
        func = app2interp_temp(target, filename=filename)
        print "executing", func
        self.execute_appex(space, func, space)

    def repr_failure(self, excinfo):
        if excinfo.errisinstance(AppError):
            excinfo = excinfo.value.excinfo
        return super(AppTestFunction, self).repr_failure(excinfo)

    def _getdynfilename(self, func):
        code = getattr(func, 'im_func', func).func_code
        return "[%s:%s]" % (code.co_filename, code.co_firstlineno)

class AppTestMethod(AppTestFunction):
    def setup(self):
        super(AppTestMethod, self).setup()
        instance = self.parent.obj
        w_instance = self.parent.w_instance
        space = instance.space
        for name in dir(instance):
            if name.startswith('w_'):
                if self.config.option.runappdirect:
                    setattr(instance, name[2:], getattr(instance, name))
                else:
                    obj = getattr(instance, name)
                    if isinstance(obj, types.MethodType):
                        source = py.std.inspect.getsource(obj).lstrip()
                        w_func = space.appexec([], textwrap.dedent("""
                        ():
                            %s
                            return %s
                        """) % (source, name))
                        w_obj = Method(space, w_func, w_instance, space.w_None)
                    else:
                        w_obj = obj
                    space.setattr(w_instance, space.wrap(name[2:]), w_obj)

    def runtest(self):
        target = self.obj
        if self.config.option.runappdirect:
            return target()
        space = target.im_self.space
        filename = self._getdynfilename(target)
        func = app2interp_temp(target.im_func, filename=filename)
        w_instance = self.parent.w_instance
        self.execute_appex(space, func, space, w_instance)

class PyPyClassCollector(py.test.collect.Class):
    def setup(self):
        cls = self.obj
        if not hasattr(cls, 'spaceconfig'):
            cls.space = LazyObjSpaceGetter()
        else:
            assert hasattr(cls, 'space') # set by pytest_runtest_setup
        super(PyPyClassCollector, self).setup()

class IntInstanceCollector(py.test.collect.Instance):
    Function = IntTestFunction

class IntClassCollector(PyPyClassCollector):
    Instance = IntInstanceCollector

    def _haskeyword(self, keyword):
        return keyword == 'interplevel' or \
               super(IntClassCollector, self)._haskeyword(keyword)

    def _keywords(self):
        return super(IntClassCollector, self)._keywords() + ['interplevel']

class AppClassInstance(py.test.collect.Instance):
    Function = AppTestMethod

    def setup(self):
        super(AppClassInstance, self).setup()
        instance = self.obj
        space = instance.space
        w_class = self.parent.w_class
        if self.config.option.runappdirect:
            self.w_instance = instance
        else:
            self.w_instance = space.call_function(w_class)

class AppClassCollector(PyPyClassCollector):
    Instance = AppClassInstance

    def _haskeyword(self, keyword):
        return keyword == 'applevel' or \
               super(AppClassCollector, self)._haskeyword(keyword)

    def _keywords(self):
        return super(AppClassCollector, self)._keywords() + ['applevel']

    def setup(self):
        super(AppClassCollector, self).setup()
        cls = self.obj
        space = cls.space
        clsname = cls.__name__
        if self.config.option.runappdirect:
            w_class = cls
        else:
            w_class = space.call_function(space.w_type,
                                          space.wrap(clsname),
                                          space.newtuple([]),
                                          space.newdict())
        self.w_class = w_class

class ExpectTestMethod(py.test.collect.Function):
    def safe_name(target):
        s = "_".join(target)
        s = s.replace("()", "paren")
        s = s.replace(".py", "")
        s = s.replace(".", "_")
        s = s.replace(os.sep, "_")
        return s

    safe_name = staticmethod(safe_name)

    def safe_filename(self):
        name = self.safe_name(self.listnames())
        num = 0
        while udir.join(name + '.py').check():
            num += 1
            name = self.safe_name(self.listnames()) + "_" + str(num)
        return name + '.py'

    def _spawn(self, *args, **kwds):
        import pexpect
        child = pexpect.spawn(*args, **kwds)
        child.logfile = sys.stdout
        return child

    def spawn(self, argv):
        return self._spawn(sys.executable, argv)

    def runtest(self):
        target = self.obj
        import pexpect
        source = py.code.Source(target)[1:].deindent()
        filename = self.safe_filename()
        source.lines = ['import sys',
                      'sys.path.insert(0, %s)' % repr(os.path.dirname(pypydir))
                        ] + source.lines
        source.lines.append('print "%s ok!"' % filename)
        f = udir.join(filename)
        f.write(source)
        # run target in the guarded environment
        child = self.spawn([str(f)])
        import re
        child.expect(re.escape(filename + " ok!"))

class ExpectClassInstance(py.test.collect.Instance):
    Function = ExpectTestMethod

class ExpectClassCollector(py.test.collect.Class):
    Instance = ExpectClassInstance

    def setup(self):
        super(ExpectClassCollector, self).setup()
        try:
            import pexpect
        except ImportError:
            py.test.skip("pexpect not found")


def pytest_ignore_collect(path):
    return path.check(link=1)

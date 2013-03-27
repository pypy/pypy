import py, pytest, sys, os, textwrap
from inspect import isclass

# pytest settings
rsyncdirs = ['.', '../lib-python', '../lib_pypy', '../demo']
rsyncignore = ['_cache']

# PyPy's command line extra options (these are added
# to py.test's standard options)
#
option = None

pypydir = os.path.realpath(os.path.dirname(__file__))

def braindead_deindent(self):
    """monkeypatch that wont end up doing stupid in the python tokenizer"""
    text = '\n'.join(self.lines)
    short = py.std.textwrap.dedent(text)
    newsource = py.code.Source()
    newsource.lines[:] = short.splitlines()
    return newsource

py.code.Source.deindent = braindead_deindent

def pytest_report_header():
    return "pytest-%s from %s" % (pytest.__version__, pytest.__file__)

def pytest_addhooks(pluginmanager):
    from rpython.conftest import LeakFinder
    pluginmanager.register(LeakFinder())

def pytest_configure(config):
    global option
    option = config.option

def pytest_addoption(parser):
    from rpython.conftest import pytest_addoption
    pytest_addoption(parser)
    
    group = parser.getgroup("pypy options")
    group.addoption('-A', '--runappdirect', action="store_true",
           default=False, dest="runappdirect",
           help="run applevel tests directly on python interpreter (not through PyPy)")
    group.addoption('--direct', action="store_true",
           default=False, dest="rundirect",
           help="run pexpect tests directly")

def pytest_funcarg__space(request):
    from pypy.tool.pytest.objspace import gettestobjspace
    spaceconfig = getattr(request.cls, 'spaceconfig', {})
    return gettestobjspace(**spaceconfig)


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
            for name in self.listnames():
                if "app_test" in name or "test_lib_pypy" in name:
                    return True
            return False
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
        return False

    def makeitem(self, name, obj):
        if isclass(obj) and self.classnamefilter(name):
            if name.startswith('AppTest'):
                from pypy.tool.pytest.apptest import AppClassCollector
                return AppClassCollector(name, parent=self)
            else:
                from pypy.tool.pytest.inttest import IntClassCollector
                return IntClassCollector(name, parent=self)

        elif hasattr(obj, 'func_code') and self.funcnamefilter(name):
            if name.startswith('app_test_'):
                assert not obj.func_code.co_flags & 32, \
                    "generator app level functions? you must be joking"
                from pypy.tool.pytest.apptest import AppTestFunction
                return AppTestFunction(name, parent=self)
            elif obj.func_code.co_flags & 32: # generator function
                return pytest.Generator(name, parent=self)
            else:
                from pypy.tool.pytest.inttest import IntTestFunction
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
        from pypy.tool.pytest.objspace import gettestobjspace
        space = gettestobjspace()
        if cls:
            cls.space = space
        return space


def pytest_runtest_setup(__multicall__, item):
    if isinstance(item, py.test.collect.Function):
        appclass = item.getparent(PyPyClassCollector)
        if appclass is not None:
            # Make cls.space and cls.runappdirect available in tests.
            spaceconfig = getattr(appclass.obj, 'spaceconfig', None)
            if spaceconfig is not None:
                from pypy.tool.pytest.objspace import gettestobjspace
                appclass.obj.space = gettestobjspace(**spaceconfig)
            appclass.obj.runappdirect = option.runappdirect

    __multicall__.execute()

def pytest_runtest_teardown(__multicall__, item):
    __multicall__.execute()

    if 'pygame' in sys.modules:
        assert option.view, ("should not invoke Pygame "
                             "if conftest.option.view is False")


class PyPyClassCollector(py.test.collect.Class):
    # All pypy Test classes have a "space" member.
    def setup(self):
        cls = self.obj
        if not hasattr(cls, 'spaceconfig'):
            cls.space = LazyObjSpaceGetter()
        else:
            assert hasattr(cls, 'space') # set by pytest_runtest_setup
        super(PyPyClassCollector, self).setup()


def pytest_ignore_collect(path):
    return path.check(link=1)

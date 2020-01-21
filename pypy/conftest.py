import py, pytest, sys, textwrap
from inspect import isclass

APPLEVEL_FN = 'apptest_*.py'

# pytest settings
rsyncdirs = ['.', '../lib-python', '../lib_pypy', '../demo']
rsyncignore = ['_cache']

try:
    from hypothesis import settings, __version__
except ImportError:
    pass
else:
    try:
        settings.register_profile('default', deadline=None)
    except Exception:
        import warnings
        warnings.warn("Version of hypothesis too old, "
                      "cannot set the deadline to None")
    settings.load_profile('default')

# PyPy's command line extra options (these are added
# to py.test's standard options)
#
option = None

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

@pytest.hookimpl(tryfirst=True)
def pytest_cmdline_preparse(config, args):
    if not (set(args) & {'-D', '--direct-apptest'}):
        args.append('--assert=reinterp')

def pytest_configure(config):
    global option
    option = config.option
    mode_A = config.getoption('runappdirect')
    mode_D = config.getoption('direct_apptest')
    if mode_D or not mode_A:
        config.addinivalue_line('python_files', APPLEVEL_FN)
    if not mode_A and not mode_D:  # 'own' tests
        from rpython.conftest import LeakFinder
        config.pluginmanager.register(LeakFinder())

def pytest_addoption(parser):
    group = parser.getgroup("pypy options")
    group.addoption('-A', '--runappdirect', action="store_true",
           default=False, dest="runappdirect",
           help="run legacy applevel tests directly on python interpreter (not through PyPy)")
    group.addoption('-D', '--direct-apptest', action="store_true",
           default=False, dest="direct_apptest",
           help="run applevel_XXX.py tests directly on host interpreter")
    group.addoption('--direct', action="store_true",
           default=False, dest="rundirect",
           help="run pexpect tests directly")
    group.addoption('--raise-operr', action="store_true",
            default=False, dest="raise_operr",
            help="Show the interp-level OperationError in app-level tests")
    group.addoption('--applevel-rewrite', action="store_true",
            default=False, dest="applevel_rewrite",
            help="Use assert rewriting in app-level test files (slow)")

@pytest.fixture(scope='class')
def spaceconfig(request):
    return getattr(request.cls, 'spaceconfig', {})

@pytest.fixture(scope='function')
def space(spaceconfig):
    from pypy.tool.pytest.objspace import gettestobjspace
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
    if path.fnmatch(APPLEVEL_FN):
        if parent.config.getoption('direct_apptest'):
            return
        from pypy.tool.pytest.apptest2 import AppTestModule
        rewrite = parent.config.getoption('applevel_rewrite')
        return AppTestModule(path, parent, rewrite_asserts=rewrite)
    else:
        return PyPyModule(path, parent)

def is_applevel(item):
    from pypy.tool.pytest.apptest import AppTestMethod
    return isinstance(item, AppTestMethod)

def pytest_collection_modifyitems(config, items):
    if config.getoption('runappdirect') or config.getoption('direct_apptest'):
        return
    for item in items:
        if isinstance(item, py.test.Function):
            if is_applevel(item):
                item.add_marker('applevel')
            else:
                item.add_marker('interplevel')


class PyPyModule(pytest.Module):
    """ we take care of collecting classes both at app level
        and at interp-level (because we need to stick a space
        at the class) ourselves.
    """
    def accept_regular_test(self):
        if self.config.option.runappdirect:
            # only collect regular tests if we are in test_lib_pypy
            for name in self.listnames():
                if "test_lib_pypy" in name:
                    return True
            return False
        return True

    def funcnamefilter(self, name):
        if name.startswith('test_'):
            return self.accept_regular_test()
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
        return super(PyPyModule, self).makeitem(name, obj)

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

@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    if isinstance(item, py.test.collect.Function):
        config = item.config
        if (item.get_marker(name='pypy_only') and
                not '__pypy__' in sys.builtin_module_names):
            pytest.skip('PyPy-specific test')
        appclass = item.getparent(py.test.Class)
        if appclass is not None:
            from pypy.tool.pytest.objspace import gettestobjspace
            # Make cls.space and cls.runappdirect available in tests.
            spaceconfig = getattr(appclass.obj, 'spaceconfig', {})
            if not (config.getoption('runappdirect') or config.getoption('direct_apptest')):
                spaceconfig.setdefault('objspace.std.reinterpretasserts', True)
            appclass.obj.space = gettestobjspace(**spaceconfig)
            appclass.obj.runappdirect = config.option.runappdirect

def pytest_ignore_collect(path, config):
    if (config.getoption('direct_apptest') and not path.isdir()
            and not path.fnmatch(APPLEVEL_FN)):
        return True
    return path.check(link=1)

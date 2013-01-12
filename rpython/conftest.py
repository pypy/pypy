from os.path import *
import py, pytest

cdir = realpath(join(dirname(__file__), 'translator', 'c'))
cache_dir = realpath(join(dirname(__file__), '_cache'))
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
    return "pytest-%s from %s" %(pytest.__version__, pytest.__file__)

def pytest_configure(config):
    global option
    option = config.option

def _set_platform(opt, opt_str, value, parser):
    from rpython.config.translationoption import PLATFORMS
    from rpython.translator.platform import set_platform
    if value not in PLATFORMS:
        raise ValueError("%s not in %s" % (value, PLATFORMS))
    set_platform(value, None)

def pytest_addoption(parser):
    group = parser.getgroup("rpython options")
    group.addoption('--view', action="store_true", dest="view", default=False,
           help="view translation tests' flow graphs with Pygame")
    group.addoption('-P', '--platform', action="callback", type="string",
           default="host", callback=_set_platform,
           help="set up tests to use specified platform as compile/run target")
    group = parser.getgroup("JIT options")
    group.addoption('--viewloops', action="store_true",
           default=False, dest="viewloops",
           help="show only the compiled loops")

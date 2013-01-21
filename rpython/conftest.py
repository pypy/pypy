from os.path import *
import py

pytest_plugins = [
    'rpython.tool.pytest.expecttest',
    'rpython.tool.pytest.leakfinder',
    'rpython.tool.pytest.platform',
    'rpython.tool.pytest.viewerplugin',
]

cdir = realpath(join(dirname(__file__), 'translator', 'c'))
cache_dir = realpath(join(dirname(__file__), '_cache'))
option = None

def pytest_configure(config):
    global option
    option = config.option


def pytest_pycollect_makeitem(__multicall__,collector, name, obj):
    res = __multicall__.execute()
    # work around pytest issue 251
    import inspect
    if res is None and inspect.isclass(obj) and \
            collector.classnamefilter(name):
        return py.test.collect.Class(name, parent=collector)
    return res



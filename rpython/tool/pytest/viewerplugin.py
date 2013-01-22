"""
    pypy.tool.pytest.viewerplugin
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    this pytest plugin is support code for
    testsuites using translation flowgraphs
    or jit loop graphs.

    it can be enabled by
    
    * adding the module name to pytest_plugins in a conftest
    * putting "-p pypy.tool.pytest.viewerplugin"
      into pytest.ini
"""
import sys
import pytest

def pytest_addoption(parser):

    group = parser.getgroup("rpython options")
    group.addoption('--view', action="store_true", dest="view", default=False,
           help="view translation tests' flow graphs with Pygame")

    group = parser.getgroup("JIT options")
    group.addoption('--viewloops', action="store_true",
           default=False, dest="viewloops",
           help="show only the compiled loops")


def maybe_show_graph(graph):
    if pytest.config.view:
        graph.show()


@pytest.mark.tryfirst
def pytest_runtest_teardown(__multicall__, item):
    __multicall__.execute()

    if 'pygame' in sys.modules:
        assert item.config.option.view, ("should not invoke Pygame "
                                         "if view option is False")


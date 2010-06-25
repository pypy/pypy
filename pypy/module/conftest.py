import py
from pypy.tool.lib_pypy import LIB_PYPY

class MultipleDirCollector(py.test.collect.Collector):
    def __init__(self, name, mainfspath, fspaths, parent=None, config=None):
        super(MultipleDirCollector, self).__init__(name, parent, config)
        self.main_collector = py.test.collect.Directory(mainfspath, self)
        self.collectors = [py.test.collect.Directory(fspath, self)
                           for fspath in fspaths]

    def collect(self):
        return self.main_collector.collect() + self.collectors


def pytest_collect_directory(path, parent):
    if path.basename == 'test_lib_pypy':
        # collect all the test in BOTH test_lib_pypy and ../../lib_pypy
        return MultipleDirCollector(path.basename, path, [LIB_PYPY], parent)

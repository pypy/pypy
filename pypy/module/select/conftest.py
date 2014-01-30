import pypy._py as py

def pytest_collect_directory():
    py.test.importorskip("ctypes")

import sys
import py.test

def pytest_runtest_setup(item):
    py.test.importorskip('greenlet')
    if sys.platform == 'win32':
        py.test.skip("stackless tests segfault on Windows")


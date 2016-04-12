"""
This disables the backend tests on non zarch platforms.
Note that you need "--slow" to run translation tests.
"""
import py, os
from rpython.jit.backend import detect_cpu

cpu = detect_cpu.autodetect()

def pytest_collect_directory(path, parent):
    if not cpu.startswith('s390x'):
        py.test.skip("zarch tests skipped: cpu is %r" % (cpu,))
pytest_collect_file = pytest_collect_directory

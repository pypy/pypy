"""
This conftest disables the backend tests on non PPC platforms
"""
import py, os
from rpython.jit.backend import detect_cpu

cpu = detect_cpu.autodetect()

def pytest_collect_directory(path, parent):
    if not cpu.startswith('ppc'):
        py.test.skip("PPC tests skipped: cpu is %r" % (cpu,))
pytest_collect_file = pytest_collect_directory

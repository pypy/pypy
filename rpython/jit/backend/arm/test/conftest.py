"""
This conftest adds an option to run the translation tests which by default will
be disabled.
Also it disables the backend tests on non ARMv7 platforms
"""
import py, os
from rpython.jit.backend import detect_cpu

cpu = detect_cpu.autodetect()

def pytest_addoption(parser):
    group = parser.getgroup('translation test options')
    group.addoption('--run-translation-tests',
                    action="store_true",
                    default=False,
                    dest="run_translation_tests",
                    help="run tests that translate code")

def pytest_collect_directory(path, parent):
    if not cpu.startswith('arm'):
        py.test.skip("ARM(v7) tests skipped: cpu is %r" % (cpu,))
pytest_collect_file = pytest_collect_directory

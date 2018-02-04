import pytest
import sys

def pytest_configure(config):
    if sys.platform.startswith('linux'):
        from rpython.rlib.rvmprof.cintf import configure_libbacktrace_linux
        configure_libbacktrace_linux()

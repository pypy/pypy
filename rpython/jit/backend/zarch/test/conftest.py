"""
This disables the backend tests on non zarch platforms.
Note that you need "--slow" to run translation tests.
"""
import os
import pytest
from rpython.jit.backend import detect_cpu

cpu = detect_cpu.autodetect()
IS_ZARCH = cpu.startswith('zarch')
THIS_DIR = os.path.dirname(__file__)

@pytest.hookimpl(tryfirst=True)
def pytest_ignore_collect(path, config):
    path = str(path)
    if not IS_ZARCH:
        if os.path.commonprefix([path, THIS_DIR]) == THIS_DIR:  # workaround for bug in pytest<3.0.5
            return True

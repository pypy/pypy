import py
import pytest

def pytest_configure(config):
    from pypy.tool.pytest.objspace import gettestobjspace
    # For some reason (probably a ll2ctypes cache issue on linux64)
    # it's necessary to run "import time" at least once before any
    # other cpyext test, otherwise the same statement will fail in
    # test_datetime.py.
    space = gettestobjspace(usemodules=['time'])
    space.getbuiltinmodule("time")

def pytest_ignore_collect(path, config):
    if config.option.runappdirect:
        return True # "cannot be run by py.test -A"
    # ensure additional functions are registered
    import pypy.module.cpyext.test.test_cpyext
    return False

def pytest_funcarg__space(request):
    return request.cls.api

def pytest_funcarg__api(request):
    return request.cls.api


import os
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
    # ensure additional functions are registered
    import pypy.module.cpyext.test.test_cpyext
    return False

def pytest_funcarg__space(request):
    return request.cls.api

def pytest_funcarg__api(request):
    return request.cls.api

if os.name == 'nt':
    @pytest.yield_fixture(autouse=True, scope='session')
    def prevent_dialog_box():
        """Do not open dreaded dialog box on segfault on Windows"""
        import ctypes
        SEM_NOGPFAULTERRORBOX = 0x0002  # From MSDN
        old_err_mode = ctypes.windll.kernel32.GetErrorMode()
        new_err_mode = old_err_mode | SEM_NOGPFAULTERRORBOX
        ctypes.windll.kernel32.SetErrorMode(new_err_mode)
        yield
        ctypes.windll.kernel32.SetErrorMode(old_err_mode)

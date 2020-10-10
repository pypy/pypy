import os
import pytest
import sys

disabled = None
THIS_DIR = os.path.dirname(__file__)

if sys.maxsize > 2**32 and sys.platform == 'win32':
    # cpyext not yet supported on windows 64 bit
    disabled = True

def pytest_ignore_collect(path, config):
    path = str(path)
    if disabled:
        if os.path.commonprefix([path, THIS_DIR]) == THIS_DIR:  # workaround for bug in pytest<3.0.5
            return True

def pytest_collect_file(path, parent):
    if disabled:
        # We end up here when calling py.test .../test_foo.py directly
        # It's OK to kill the whole session with the following line
        pytest.skip("cpyext not yet supported on windows 64 bit")

def pytest_configure(config):
    if config.getoption('runappdirect') or config.getoption('direct_apptest'):
        import py
        from pypy import pypydir
        sys.path.append(str(py.path.local(pypydir) / 'tool' / 'cpyext'))
        return
    from pypy.tool.pytest.objspace import gettestobjspace
    # For some reason (probably a ll2ctypes cache issue on linux64)
    # it's necessary to run "import time" at least once before any
    # other cpyext test, otherwise the same statement will fail in
    # test_datetime.py.
    space = gettestobjspace(usemodules=['time'])
    space.getbuiltinmodule("time")

    # ensure additional functions are registered
    import pypy.module.cpyext.test.test_cpyext


@pytest.fixture
def api(request):
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

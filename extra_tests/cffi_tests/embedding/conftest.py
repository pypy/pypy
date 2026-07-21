
import pytest
import sys


disabled = False

if '__pypy__' in sys.builtin_module_names:
    try:
        import cpyext
    except Exception:
        disabled = True

def pytest_ignore_collect(path, config):
    if disabled:
        return True

def pytest_collect_file(path, parent):
    if disabled:
        # We end up here when calling py.test .../test_foo.py directly
        # It's OK to kill the whole session with the following line
        pytest.skip("cpyext not present")



import os
import pytest
import sys

translated = sys.version_info[0] > 2
if translated:
    try:
        import _numpypy
        disabled = False
    except Exception as e:
        disabled= True
else:
    from pypy.config import pypyoption
    disabled= 'micronumpy' not in pypyoption.working_modules

THIS_DIR = os.path.dirname(__file__)

if sys.maxsize > 2**32 and sys.platform == 'win32':
    # micronumpy not yet supported on windows 64 bit
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
        pytest.skip("cpyext not tested on this platform")

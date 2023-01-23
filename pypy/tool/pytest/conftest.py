from pypy.conftest import pytest_configure as _configure

try:
    import builtins
except ImportError:
    import sys
    sys.modules['builtins'] = __builtins__

def pytest_configure(config):
    _configure(config)
    # When using pytester plugin, we need these settings:
    config.option.runpytest = 'subprocess'
    config.option.assertmode = 'rewrite'

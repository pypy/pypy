import os
import pytest
import sys

if sys.platform == 'win32':
    def pytest_configure(config):
        if config.getoption('runappdirect') or config.getoption('direct_apptest'):
            return
        # Set up the compiler via rpython.platform
        from rpython.translator.platform import host
        for key in ('PATH', 'LIB', 'INCLUDE'):
            os.environ[key] = host.c_environ[key]
        os.environ['DISTUTILS_USE_SDK'] = "1"
        os.environ['MSSdk'] = "1"

def pytest_collection_modifyitems(config, items):
    if config.getoption('runappdirect') or config.getoption('direct_apptest'):
        skip = pytest.mark.skip(reason="PyPy2.7 does not warn")
        for item in items:
            if item.name == "test_more_buffer_warning":
                item.add_marker(skip)

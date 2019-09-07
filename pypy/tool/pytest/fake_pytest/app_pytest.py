import pytest


def importorskip(name):
    try:
        return __import__(name)
    except ImportError:
        pytest.skip('Module %s not available' % name)

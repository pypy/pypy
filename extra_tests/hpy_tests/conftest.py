import sys
try:
    import _hpy_universal
    disable = False
except ImportError:
    disable = True

if sys.platform == "win32":
    disable = True

def pytest_ignore_collect(path, config):
    return disable



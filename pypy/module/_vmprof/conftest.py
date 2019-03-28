import py, platform, sys

def pytest_collect_directory(path, parent):
    if platform.machine() == 's390x':
        py.test.skip("_vmprof tests skipped")
    if sys.platform == 'win32':
        py.test.skip("_vmprof tests skipped")
pytest_collect_file = pytest_collect_directory

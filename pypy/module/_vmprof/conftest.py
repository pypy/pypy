import py, platform

def pytest_collect_directory(path, parent):
    if platform.machine() == 's390x':
        py.test.skip("zarch tests skipped")
pytest_collect_file = pytest_collect_directory

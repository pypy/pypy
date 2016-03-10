import py, os

def pytest_collect_directory(path, parent):
    if os.uname()[4] == 's390x':
        py.test.skip("zarch tests skipped")
pytest_collect_file = pytest_collect_directory

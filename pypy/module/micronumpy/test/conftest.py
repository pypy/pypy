import py

def pytest_collect_directory(path, parent):
    py.test.skip("micronumpy tests skipped for now on py3.5")
pytest_collect_file = pytest_collect_directory

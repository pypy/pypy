import py

def pytest_collect_directory(path):
    py.test.skip("CLI backend tests skipped for now")

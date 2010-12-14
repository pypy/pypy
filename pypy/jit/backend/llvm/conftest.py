import py

def pytest_collect_directory():
    py.test.skip("llvm backend tests skipped for now")

import py

def pytest_runtest_setup(item):
    if py.path.local.sysfind('genreflex') is None:
        py.test.skip("genreflex is not installed")

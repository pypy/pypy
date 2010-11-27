import py

option = py.test.config.option

def pytest_addoption(parser):
    group = parser.getgroup("JIT options")
    group.addoption('--slow', action="store_true",
           default=False, dest="run_slow_tests",
           help="run all the compiled tests (instead of just a few)")
    group.addoption('--viewloops', action="store_true",
           default=False, dest="viewloops",
           help="show only the compiled loops")


def pytest_addoption(parser):
    group = parser.addgroup("pypyjit options")
    group.addoption("--pypy", action="store", default=None, dest="pypy_c",
                    help="the location of the JIT enabled pypy-c")


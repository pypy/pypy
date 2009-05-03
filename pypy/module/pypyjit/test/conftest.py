class PyPyJitTestPlugin:
    def pytest_addoption(self, parser):
        group = parser.addgroup("pypyjit options")
        group.addoption("--pypy-c", action="store", default=None, dest="pypy_c",
                        help="the location of the JIT enabled pypy-c")

ConftestPlugin = PyPyJitTestPlugin

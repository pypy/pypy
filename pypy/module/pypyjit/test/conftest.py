def pytest_addoption(parser):
    group = parser.getgroup("pypyjit options")
    group.addoption("--pypy", action="store", default=None, dest="pypy_c",
                    help="DEPRECATED: use this in test_pypy_c instead")
# XXX kill the corresponding section in the buildbot run,
# which (as far as I can tell) ignores that option entirely and does
# the same as the regular py.test.

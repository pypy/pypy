def pytest_addoption(parser):
    group = parser.getgroup("pypyjit.py options")
    group.addoption('--ootype', action="store_true", dest="ootype",
                    default=False,
                    help="use ootype")

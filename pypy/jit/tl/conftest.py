class ConftestPlugin:
    def pytest_addoption(self, parser):
        group = parser.addgroup("pypyjit.py options")
        group.addoption('--ootype', action="store_true", dest="ootype", default=False,
                help="use ootype")

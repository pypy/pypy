class ConftestPlugin:
    def pytest_addoption(self, parser):
        group = parser.addgroup("pypy-ojs options")
        group.addoption('--use-browser', action="store", dest="browser", type="string",
                default="", help="run Javascript tests in your default browser")
        group.addoption('--tg', action="store_true", dest="tg", default=False,
                help="Use TurboGears machinery for testing")

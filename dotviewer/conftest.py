import py

class ConftestPlugin:
    def pytest_addoption(self, parser):
        group = parser.addgroup("dotviever")
        group.addoption('--pygame', action="store_true", 
            dest="pygame", default=False, 
            help="allow interactive tests using Pygame")

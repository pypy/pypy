import py

Option = py.test.config.Option
option = py.test.config.addoptions("dotviewer options",
        Option('--pygame', action="store_true", dest="pygame", default=False,
               help="allow interactive tests using Pygame"),
        )

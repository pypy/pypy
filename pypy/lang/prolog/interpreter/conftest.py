import py, sys

rootdir = py.magic.autopath().dirpath()

Option = py.test.config.Option

option = py.test.config.addoptions("prolog options", 
        Option('--slow', action="store_true", dest="slow", default=False,
               help="view translation tests' flow graphs with Pygame"),
    )

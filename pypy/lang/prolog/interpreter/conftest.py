import py, sys

rootdir = py.magic.autopath().dirpath()

Option = py.test.Config.Option

option = py.test.Config.addoptions("prolog options", 
        Option('--slow', action="store_true", dest="slow", default=False,
               help="view translation tests' flow graphs with Pygame"),
    )

import py
Option = py.test.Config.Option

option = py.test.Config.addoptions("codegen options",
        Option('--trap', action="store_true", default=False,
               dest="trap",
               help="generate a breakpoint instruction at the start"))

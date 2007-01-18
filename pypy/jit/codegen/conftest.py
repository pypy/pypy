import py
Option = py.test.config.Option

option = py.test.config.addoptions("codegen options",
        Option('--trap', action="store_true", default=False,
               dest="trap",
               help="generate a breakpoint instruction at the start"))

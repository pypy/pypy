import py


Option = py.test.config.Option

option = py.test.config.addoptions("ppc options",
        Option('--pypy-c', action="store", default=None,
               dest="pypy_c",
               help=""))

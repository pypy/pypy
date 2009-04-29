import py

Option = py.test.config.Option

option = py.test.config.addoptions\
         ("pypy-cli options", 

          Option('--source', action="store_true", dest="source", default=False,
                 help="only generate IL source, don't compile"),

          Option('--wd', action="store_true", dest="wd", default=False,
                 help="store temporary files in the working directory"),

          Option('--stdout', action="store_true", dest="stdout", default=False,
                 help="print the generated IL code to stdout, too"),

          Option('--nostop', action="store_true", dest="nostop", default=False,
                 help="don't stop on warning. The generated IL code could not compile"),

          Option('--nowrap', action="store_true", dest="nowrap", default=False,
                 help="don't wrap exceptions but let them to flow out of the entry point"),

          Option('--verify', action="store_true", dest="verify", default=False,
                 help="check that compiled executables are verifiable"),

          Option('--norun', action='store_true', dest="norun", default=False,
                 help="don't run the compiled executable"),

          Option('--trace', action='store_true', dest='trace', default=False,
                 help='Trace execution of generated code'),
          )




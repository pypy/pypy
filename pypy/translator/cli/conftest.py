import py

Option = py.test.Config.Option

option = py.test.Config.addoptions\
         ("pypy-cli options", 

          Option('--source', action="store_true", dest="source", default=False,
                 help="only generate IL source, don't compile"),

          Option('--wd', action="store_true", dest="wd", default=False,
                 help="store temporary files in the working directory"),

          Option('--stdout', action="store_true", dest="stdout", default=False,
                 help="print the generated IL code to stdout, too"),

          Option('--nostop', action="store_true", dest="nostop", default=False,
                 help="don't stop on warning. The generated IL code could not compile")
          )


def pytest_addoption(parser):
    group = parser.getgroup("pypy-cli options")
    group.addoption('--source', action="store_true", dest="source", default=False,
            help="only generate IL source, don't compile")
    group.addoption('--wd', action="store_true", dest="wd", default=False,
            help="store temporary files in the working directory")
    group.addoption('--stdout', action="store_true", dest="stdout", default=False,
            help="print the generated IL code to stdout, too")
    group.addoption('--nostop', action="store_true", dest="nostop", default=False,
            help="don't stop on warning. The generated IL code could not compile")
    group.addoption('--nowrap', action="store_true", dest="nowrap", default=False,
            help="don't wrap exceptions but let them to flow out of the entry point")
    group.addoption('--verify', action="store_true", dest="verify", default=False,
            help="check that compiled executables are verifiable")
    group.addoption('--norun', action='store_true', dest="norun", default=False,
            help="don't run the compiled executable")
    group.addoption('--trace', action='store_true', dest='trace', default=False,
            help='Trace execution of generated code')

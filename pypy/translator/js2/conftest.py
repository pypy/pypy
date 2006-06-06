import py

Option = py.test.Config.Option

option = py.test.Config.addoptions("pypy-js options", 
        Option('--browser', action="store_true",dest="browser", 
               default=False, help="run Javascript tests in your default browser"),
    )

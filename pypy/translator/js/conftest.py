import py

Option = py.test.Config.Option

option = py.test.Config.addoptions("pypy options", 
        Option('--browser', action="store_true",dest="jsbrowser", 
               default=False, help="run JS tests in a browser"),
    )

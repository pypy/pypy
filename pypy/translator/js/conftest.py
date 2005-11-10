import py

Option = py.test.Config.Option

option = py.test.Config.addoptions("pypy-js options", 
        Option('--browser', action="store_true",dest="jsbrowser", 
               default=False, help="run Javscript tests in your (default) browser"),
    )

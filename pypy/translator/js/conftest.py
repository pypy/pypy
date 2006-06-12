import py

Option = py.test.Config.Option

option = py.test.Config.addoptions("pypy-ojs options", 
        Option('--use-browser', action="store", dest="browser", type="string",
               default="", help="run Javascript tests in your default browser"),
        
        Option('--tg', action="store_true", dest="tg", default=False,
            help="Use TurboGears machinery for testing")
    )

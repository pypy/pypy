import py

Option = py.test.Config.Option

option = py.test.Config.addoptions("pypy-js options", 
        Option('--browser', action="store_true",dest="jsbrowser", 
               default=False, help="run Javascript tests in your default browser"),
        Option('--stackless', action="store_true",dest="jsstackless", 
               default=False, help="enable stackless feature"),
        Option('--compress', action="store_true",dest="jscompress", 
               default=False, help="enable javascript compression"),
        Option('--log', action="store_true",dest="jslog", 
               default=False, help="log debugging info"),
    )

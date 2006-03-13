import py

Option = py.test.Config.Option

option = py.test.Config.addoptions("pypy-squeak options", 
        Option('--showsqueak', action="store_true", dest="showsqueak", 
               default=False, help="don't run squeak headless, for debugging"),
    )

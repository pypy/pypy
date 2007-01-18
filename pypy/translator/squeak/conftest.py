import py

Option = py.test.config.Option

option = py.test.config.addoptions("pypy-squeak options", 
        Option('--showsqueak', action="store_true", dest="showsqueak", 
               default=False, help="don't run squeak headless, for debugging"),
    )

import py

Option = py.test.Config.Option

option = py.test.Config.addoptions("pypy-ojs options", 
        Option('--use-browser', action="store", dest="browser", type="string",
               default="", help="run Javascript tests in your default browser")
    )

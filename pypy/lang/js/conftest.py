import py

Option = py.test.config.Option
option = py.test.config.addoptions("ecma compatibility tests",
        Option('', '--ecma',
               action="store_true", dest="ecma", default=False,
               help="run js interpreter ecma tests"
        ),
)

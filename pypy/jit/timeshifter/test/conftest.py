import py

Option = py.test.config.Option

option = py.test.config.addoptions("timeshifter tests options",
        Option('--dump', action="store_true", default=False,
               dest="use_dump_backend",
               help="uses the dump backend, to log the backend operations"),
        )

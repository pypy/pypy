import py

Option = py.test.config.Option
option = py.test.config.addoptions("smalltalk options",
        Option('--bc-trace',
               action="store_true",
               dest="bc_trace",
               default=False,
               help="print bytecodes and stack during execution"),
    )

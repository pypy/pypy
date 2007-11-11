import py

Option = py.test.config.Option

option = py.test.config.addoptions(
    "pypy-jvm options",

    Option('--java', action='store', dest='java', default='java',
           help='Define the java executable to use'),
    Option('--javac', action='store', dest='javac', default='javac',
           help='Define the javac executable to use'),
    Option('--jasmin', action='store', dest='java', default='java',
           help='Define the jasmin script to use'),
    Option('--noassemble', action='store_true', dest="noasm", default=False,
           help="don't assemble jasmin files"),
    Option('--package', action='store', dest='package', default='pypy',
           help='Package to output generated classes into'),
##    Option('--trace', action='store_true', dest='trace', default=False,
##           help='Trace execution of generated code'),
    Option('--byte-arrays', action='store_true', dest='byte-arrays',
           default=False, help='Use byte arrays rather than native strings'),
    )

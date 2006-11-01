import py

Option = py.test.Config.Option

option = py.test.Config.addoptions(
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
    Option('--trace', action='store_true', dest='trace', default=False,
           help='Trace execution of generated code')
    )

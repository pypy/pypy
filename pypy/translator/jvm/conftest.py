import py

Option = py.test.Config.Option

option = py.test.Config.addoptions(
    "pypy-jvm options",

    Option('--javac', action='store', dest='javac', default='javac',
           help='Define the java compiler to use'),
    Option('--java', action='store', dest='java', default='java',
           help='Define the java executable to use'),
##    Option('--view', action='store_true', dest='view', default=False,
##           help='View the graphs before they are generated'),
    Option('--wd', action='store_true', dest='wd', default=False,
           help='Output to current directory instead of /tmp'),
    Option('--noassemble', action='store_true', dest="noasm", default=False,
           help="don't assemble jasmin files"),
    Option('--norun', action='store_true', dest="norun", default=False,
           help="don't run the compiled executable"),
    Option('--package', action='store', dest='package', default='pypy',
           help='Package to output generated classes into')
    #Option('--opt', action='XXX', dest='YYY', default=DEF, help='HELP')
    )

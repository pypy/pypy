import py

Option = py.test.Config.Option

option = py.test.Config.addoptions(
    "pypy-jvm options",

    Option('--javac', action='', dest='javac', default='javac',
           help='Define the java compiler to use'),
    Option('--java', action='', dest='java', default='java',
           help='Define the java executable to use'),
    Option('--view', action='store_true', dest='view', default=False,
           help='View the graphs before they are generated'),
    Option('--wd', action='store_true', dest='wd', default=False,
           help='Output to current directory instead of /tmp'),
    Option('--package', action='', dest='package', default='pypy',
           help='Package to output generated classes into')
    #Option('--opt', action='XXX', dest='YYY', default=DEF, help='HELP')
    )

import py

dist_hosts = ['localhost:/tmp/jspypy', 'localhost']
dist_rsync_roots = ['../../../',]
# dist_remotepython = 'python2.4'
dist_nicelevel = 10 
dist_boxed = False
dist_maxwait = 1000 
dist_taskspernode = 10

Option = py.test.config.Option
option = py.test.config.addoptions("ecma compatibility tests",
        Option('', '--ecma',
               action="store_true", dest="ecma", default=False,
               help="run js interpreter ecma tests"
        ),
)

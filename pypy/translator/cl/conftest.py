import py

Option = py.test.Config.Option

option = py.test.Config.addoptions('pypy-cl options',
    Option('--prettyprint', action='store_true', dest='prettyprint',
        default=False, help='pretty-print Common Lisp source'))

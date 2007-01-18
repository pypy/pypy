import py

Option = py.test.config.Option

option = py.test.config.addoptions('pypy-cl options',
    Option('--prettyprint', action='store_true', dest='prettyprint',
        default=False, help='pretty-print Common Lisp source'))


def pytest_addoption(parser):
    group = parser.getgroup("pypy-jvm options")
    group.addoption('--java', action='store', dest='java', default='java',
            help='Define the java executable to use')
    group.addoption('--javac', action='store', dest='javac',
                    default='javac',
                    help='Define the javac executable to use')
    group.addoption('--jasmin', action='store', dest='java', default='java',
            help='Define the jasmin script to use')
    group.addoption('--noassemble', action='store_true', dest="noasm",
                    default=False,
                    help="don't assemble jasmin files")
    group.addoption('--package', action='store', dest='package',
                    default='pypy',
                    help='Package to output generated classes into')

    group.addoption('--byte-arrays', action='store_true',
                    dest='byte-arrays',
                    default=False,
                    help='Use byte arrays rather than native strings')


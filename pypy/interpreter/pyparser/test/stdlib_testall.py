import autopath
import py
from test_astcompiler import check_compile


def check_file_compile(filename):
    print 'Compiling:', filename
    source = open(filename).read()
    check_compile(source, 'exec', quiet=True)


def test_all():
    p = py.path.local(autopath.pypydir).dirpath().join('lib-python', '2.4.1')
    for s in p.listdir():
        if s.check(ext='.py'):
            yield check_file_compile, str(s)

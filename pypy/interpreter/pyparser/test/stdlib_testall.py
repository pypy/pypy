import autopath
import py
from test_astcompiler import check_compile

def setup_module(mod):
    import sys
    if sys.version[:3] != "2.4":
        py.test.skip("expected to work only on 2.4")
    import pypy.conftest
    mod.std_space = pypy.conftest.getobjspace('std')

def check_file_compile(filename):
    print 'Compiling:', filename
    source = open(filename).read()
    check_compile(source, 'exec', quiet=True, space=std_space)


def test_all():
    p = py.path.local(autopath.pypydir).dirpath().join('lib-python', '2.4.1')
    for s in p.listdir():
        if s.check(ext='.py'):
            yield check_file_compile, str(s)

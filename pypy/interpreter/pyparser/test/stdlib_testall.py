import pypy 
import py
from test_astcompiler import compile_with_astcompiler

def setup_module(mod):
    import sys
    if sys.version[:3] != "2.4":
        py.test.skip("expected to work only on 2.4")
    import pypy.conftest
    mod.std_space = pypy.conftest.gettestobjspace('std')

def check_file_compile(filepath):
    print 'Compiling:', filepath 
    source = filepath.read() 
    #check_compile(source, 'exec', quiet=True, space=std_space)
    compile_with_astcompiler(source, mode='exec', space=std_space)

def test_all():
    p = py.path.local(pypy.__file__).dirpath().dirpath('lib-python', '2.4.1')
    for s in p.listdir("*.py"): 
        yield check_file_compile, s 

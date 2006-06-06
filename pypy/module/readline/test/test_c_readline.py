
from pypy.module.readline import c_readline 

def test_basic_import():
    c_readline.c_rl_initialize()

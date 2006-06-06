from pypy.module.readline import Module 
from ctypes import *
from pypy.rpython.rctypes.tool.ctypes_platform import Library

#------------------------------------------------------------
# configuration for binding to external readline library 
# through rctypes
#
class CConfig:
    _header_ = """#include <readline/readline.h>"""
    readline = Library('readline')

    
    
cconfig = Module.cconfig(CConfig)

libreadline = cconfig.readline

# get a binding to  c library functions and define their args and return types
# char *readline(char *)
c_readline = libreadline.get_func('readline', [c_char_p], c_char_p)
# void rl_initiliaze(void)
c_rl_initialize = libreadline.get_func('rl_initiliaze', [], None)

#------------------------------------------------------------
# special initialization of readline 

def setup_readline(space): 
    # XXX ... 
    c_rl_initialize()

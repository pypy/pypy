from ctypes import *
from pypy.rpython.rctypes.tool.ctypes_platform import configure, Library

#------------------------------------------------------------
# configuration for binding to external readline library 
# through rctypes
#
class CConfig:
    _header_ = """#include <readline/readline.h>"""
    readline = Library('readline')

cconfig = configure(CConfig)
libreadline = cconfig['readline']


# get a binding to  c library functions and define their args and return types
# char *readline(char *)
c_readline = libreadline.readline
c_readline.argtypes = [c_char_p]
c_readline.restype = c_char_p

# void rl_initiliaze(void)
c_rl_initialize = libreadline.rl_initialize
c_rl_initialize.argtypes = []
c_rl_initialize.restype = None


#------------------------------------------------------------
# special initialization of readline 

def setup_readline(space, w_module):
    # XXX ... 
    c_rl_initialize()
    space.readline_func = readline_func

def readline_func(s):
    return c_readline(s)

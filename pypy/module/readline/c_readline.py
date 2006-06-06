from pypy.module.readline import Module 
import ctypes

#------------------------------------------------------------
# configuration for binding to external readline library 
# through rctypes
#
class CConfig:
    _header_ = """#include <readline/readline.h>"""
    _libraries_ = ('readline',)

cconfig = Module.cconfig(CConfig)

libreadline = cconfig.ctypes_lib['readline']

c_readline = libreadline.readline
c_readline.restype = ctypes.c_char_p

c_rl_initialize = libreadline.rl_initiliaze 
c_rl_initialize.argtypes = []
#c_rl_initialize.restype = void 

#------------------------------------------------------------
# special initialization of readline 

def setup_readline(space): 
    # XXX ... 
    c_rl_initialize()

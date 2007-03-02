from ctypes import *
from pypy.rpython.rctypes.tool.ctypes_platform import configure, Library
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import ObjSpace, interp2app

#------------------------------------------------------------
# configuration for binding to external readline library 
# through rctypes
#
class CConfig:
    _header_ = ""
    _includes_ = ["readline/readline.h"]
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
    c_rl_initialize()
    # install sys.__raw_input__, a hook that will be used by raw_input()
    space.setitem(space.sys.w_dict, space.wrap('__raw_input__'),
                  space.wrap(app_readline_func))

def readline_func(space, prompt):
    res = c_readline(prompt)
    if res is None:
        raise OperationError(space.w_EOFError, space.w_None)
    return space.wrap(res)
readline_func.unwrap_spec = [ObjSpace, str]
app_readline_func = interp2app(readline_func)

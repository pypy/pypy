# this is a sketch of how one might one day be able to define a pretty simple
# ctypes-using module, suitable for feeding to the ext-compiler

from pypy.interpreter.ctypesmodule import CTypesModule
from pypy.interpreter.baseobjspace import ObjSpace
import ctypes

# XXX raw_input needs to check for space.readline_func and use
# it if its there 

class Module(CTypesModule):
    """Importing this module enables command line editing using GNU readline."""
    # the above line is the doc string of the translated module  

    def init(self, space):
        setup_readline(space, self)
        space.readline_func = self.dict_w['readline']

    interpleveldefs = {
        'readline'    : '.readline',
    }

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

#------------------------------------------------------------
# exported API  (see interpleveldefs above)
#
def readline(space, w_prompt):
    prompt = space.str_w(w_prompt)
    return space.wrap(c_readline(prompt))

def setcompleter(space, w_callback):
    """Set or remove the completer function.
    The function is called as function(text, state),
    for state in 0, 1, 2, ..., until it returns a non-string.
    It should return the next possible completion starting with 'text'.
    """ 
    # XXX set internal completion function 
    

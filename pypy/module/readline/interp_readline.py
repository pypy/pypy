# this is a sketch of how one might one day be able to define a pretty simple
# ctypes-using module, suitable for feeding to the ext-compiler

from pypy.interpreter.ctypesmodule import CTypesModule
from pypy.interpreter.baseobjspace import ObjSpace

from pypy.module.readline import c_readline 

#------------------------------------------------------------
# exported API  (see interpleveldefs in __init__.py) 
#
def readline(space, w_prompt):
    prompt = space.str_w(w_prompt)
    return space.wrap(c_readline.c_readline(prompt))

def setcompleter(space, w_callback):
    """Set or remove the completer function.
    The function is called as function(text, state),
    for state in 0, 1, 2, ..., until it returns a non-string.
    It should return the next possible completion starting with 'text'.
    """ 
    # XXX set internal completion function 
    

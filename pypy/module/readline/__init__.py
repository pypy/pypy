# this is a sketch of how one might one day be able to define a pretty simple
# ctypes-using module, suitable for feeding to the ext-compiler

from pypy.interpreter.ctypesmodule import CTypesModule

# XXX raw_input needs to check for space.readline_func and use
# it if its there 

class Module(CTypesModule):
    """Importing this module enables command line editing using GNU readline."""
    # the above line is the doc string of the translated module  

    def init(self, space):
        from pypy.module.readline import c_readline 
        c_readline.setup_readline(space, self)
        space.readline_func = self.dict_w['readline']

    interpleveldefs = {
        'readline'    : 'interp_readline.readline',
    }

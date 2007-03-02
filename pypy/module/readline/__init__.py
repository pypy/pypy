# this is a sketch of how one might one day be able to define a pretty simple
# ctypes-using module, suitable for feeding to the ext-compiler

from pypy.interpreter.mixedmodule import MixedModule

# XXX raw_input needs to check for space.readline_func and use
# it if its there 

class Module(MixedModule):
    """Importing this module enables command line editing using GNU readline."""
    # the above line is the doc string of the translated module  

    def setup_after_space_initialization(self):
        from pypy.module.readline import c_readline 
        c_readline.setup_readline(self.space, self)

    interpleveldefs = {
        'readline'    : 'interp_readline.readline',
    }

    appleveldefs = {
    }

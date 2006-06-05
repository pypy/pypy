# this is a sketch of how one might one day be able to define a pretty simple
# ctypes-using module, suitable for feeding to the ext-compiler

from pypy.interpreter.ctypesmodule import CTypesModule
from pypy.interpreter.baseobjspace import ObjSpace
import ctypes

class Module(CTypesModule):
    """readline"""

    def init(self, space):
        space.readline_func = self.dict_w['readline']

    interpleveldefs = {
        'readline'    : '.readline',
    }

class CConfig:
    _header_ = """#include <readline/readline.h>"""
    _libraries_ = ('readline',)

cconfig = Module.cconfig(CConfig)

libreadline = cconfig.ctypes_lib['readline']

c_readline = libreadline.readline
c_readline.restype = ctypes.c_char_p

def readline(space, prompt):
    return space.wrap(c_readline(prompt))
readline.unwrap_spec = [ObjSpace, str]

    

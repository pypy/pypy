from pypy.interpreter import baseobjspace
from pypy.interpreter.pycode import PyCode

#######################
####  __builtin__  ####
#######################

# XXX what should methodtables be?
class methodtable:

    def chr(space, w_ascii):
        w_character = space.newstring([w_ascii])
        return w_character

import __builtin__ as _b

def compile(*args, **kwargs):
    c = _b.compile(*args, **kwargs)
    res = PyCode()
    res._from_code(c)
    return res

compile.__doc__ = _b.compile.__doc__

import baseobjspace

from pypy.interpreter.pycode import PyCode

#######################
####  __builtin__  ####
#######################

# XXX what should methodtables be?
class methodtable:

    def chr(space, w_ascii):
        w_character = space.newstring([w_ascii])
        return w_character

# redirecting certain things to the real builtins

_b = __builtins__

def compile(*args, **kwds):
    c = _b.compile(*args, **kwds)
    res = PyCode()
    res._from_code(c)
    return res
compile.__doc__ = _b.compile.__doc__

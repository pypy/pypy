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

# redirecting certain things to the real builtins
_b = __builtins__

def compile(*args, **kwargs):
    import types
    if type(_b) == types.ModuleType:
       fun = _b.compile
    else:
       fun = _b['compile']
    c = fun(*args, **kwargs)
    res = PyCode()
    res._from_code(c)
    return res

print compile("def bla(): return None", "?", "exec")

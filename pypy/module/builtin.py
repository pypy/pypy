from pypy.interpreter.extmodule import *
from pypy.interpreter.pycode import PyByteCode

#######################
####  __builtin__  ####
#######################

import __builtin__ as _b

def compile(*args, **kwargs):
    c = _b.compile(*args, **kwargs)
    res = PyByteCode()
    res._from_code(c)
    return res

##compile.__doc__ = _b.compile.__doc__


class Builtin(BuiltinModule):
    __pythonname__ = '__builtin__'

    def chr(self, w_ascii):
        w_character = self.space.newstring([w_ascii])
        return w_character
    chr = appmethod(chr)

    def len(self, w_obj):
        return self.space.len(w_obj)
    len = appmethod(len)

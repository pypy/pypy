from pypy.interpreter.extmodule import *
from pypy.interpreter.pycode import PyByteCode

#######################
####  __builtin__  ####
#######################

import __builtin__ as _b

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

    def compile(self, w_str, w_filename, w_startstr,
                w_supplied_flags, w_dont_inherit):
        str = space.unwrap(w_str)
        filename = space.unwrap(w_filename)
        startstr = space.unwrap(w_startstr)
        supplied_flags = space.unwrap(w_supplied_flags)
        dont_inherit = space.unwrap(w_dont_inherit)
        c = _b.compile(str, filename, startstr, supplied_flags, dont_inherit)
        res = PyByteCode()
        res._from_code(c)
        return space.wrap(res)
    compile = appmethod(compile)

from pypy.interpreter.extmodule import *
from pypy.interpreter.pycode import PyByteCode
from pypy.interpreter.executioncontext import OperationError

#######################
####  __builtin__  ####
#######################

import __builtin__ as _b

class Builtin(BuiltinModule):
    __pythonname__ = '__builtin__'

    def chr(self, w_ascii):
        w_character = self.space.newstring([w_ascii])
        return w_character
    chr = appmethod(chr)

    def len(self, w_obj):
        return self.space.len(w_obj)
    len = appmethod(len)


    def __import__(self,w_modulename,w_locals,w_globals,w_fromlist):
        space = self.space
        try:
            w_mod = space.getitem(space.w_modules,w_modulename)
            return w_mod
        except OperationError,e:
            if not e.match(space,space.w_KeyError):
                raise
            raise OperationError(space.w_ImportError)
    __import__ = appmethod(__import__)

    def compile(self, w_str, w_filename, w_startstr,
                w_supplied_flags=None, w_dont_inherit=None):
        space = self.space
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

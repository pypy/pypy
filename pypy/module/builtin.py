from pypy.interpreter.extmodule import *
from pypy.interpreter import pycode, appfile, executioncontext

#######################
####  __builtin__  ####
#######################

import __builtin__ as _b

class Builtin(BuiltinModule):
    __pythonname__ = '__builtin__'
    __appfile__ = appfile.AppFile(__name__, ["module"])

    def chr(self, w_ascii):
        w_character = self.space.newstring([w_ascii])
        return w_character
    chr = appmethod(chr)

    def len(self, w_obj):
        return self.space.len(w_obj)
    len = appmethod(len)

    def str(self, w_obj):
        return self.space.str(w_obj)
    str = appmethod(str)

    # temporary hack, until we have a real tuple type for calling
    def tuple(self, w_obj):
        lis = self.space.unpackiterable(w_obj)
        w_res = self.space.newtuple(lis)
        return w_res
    tuple = appmethod(tuple)

    def __import__(self, w_modulename, w_locals, w_globals, w_fromlist):
        space = self.space
        try:
            w_mod = space.getitem(space.w_modules, w_modulename)
            return w_mod
        except executioncontext.OperationError,e:
            if not e.match(space, space.w_KeyError):
                raise
            w_mod = space.get_builtin(w_modulename)
            if w_mod is not None:
                space.setitem(space.w_modules,w_modulename,w_mod)
                return w_mod
            raise executioncontext.OperationError(
                      space.w_ImportError, w_modulename)
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
        res = pycode.PyByteCode()
        res._from_code(c)
        return space.wrap(res)
    compile = appmethod(compile)


    ####essentially implemented by the objectspace
    def abs(self, w_val):
        pass
    abs = appmethod(abs)


    def chr(self, w_val):
        pass
    chr = appmethod(chr)


    def delattr(self, w_val):
        pass
    delattr = appmethod(delattr)


    def getattr(self, w_val):
        pass
    getattr = appmethod(getattr)


    def hash(self, w_val):
        pass
    hash = appmethod(hash)


    def hex(self, w_val):
        pass
    hex = appmethod(hex)


    def id(self, w_val):
        pass
    id = appmethod(id)


    def isinstance(self, w_val):
        pass
    isinstance = appmethod(isinstance)


    def issubclass(self, w_val):
        pass
    issubclass = appmethod(issubclass)


    def iter(self, w_val):
        pass
    iter = appmethod(iter)


    def len(self, w_val):
        pass
    len = appmethod(len)


    def eon(self, w_val):
        pass
    eon = appmethod(eon)


    def ord(self, w_val):
        pass
    ord = appmethod(ord)


    def pow(self, w_val):
        pass
    pow = appmethod(pow)


    def repr(self, w_val):
        pass
    repr = appmethod(repr)


    def setattr(self, w_val):
        pass
    setattr = appmethod(setattr)


    def unichr(self, w_val):
        pass
    unichr = appmethod(unichr)



from pypy.interpreter.extmodule import *
from pypy.interpreter import pycode, appfile, executioncontext

#######################
####  __builtin__  ####
#######################

import __builtin__ as _b

class Builtin(BuiltinModule):
    __pythonname__ = '__builtin__'
    __appfile__ = appfile.AppFile(__name__, ["module"])

    __helper_appfile__ = appfile.AppFile('builtin_helper',["module"])

    # temporary hack, until we have a real tuple type for calling
    #def tuple(self, w_obj):
    #    lis = self.space.unpackiterable(w_obj)
    #    w_res = self.space.newtuple(lis)
    #    return w_res
    #tuple = appmethod(tuple)

    def _actframe(self):
        return self.space.getexecutioncontext().framestack.top()


    def globals(self):
        return self._actframe().w_globals
    globals = appmethod(globals)

    def locals(self):
        return self._actframe().w_locals
    locals = appmethod(locals)


    def __import__(self, w_modulename, w_locals, w_globals, w_fromlist):
        space = self.space
        w = space.wrap
        try:
            w_mod = space.getitem(space.w_modules, w_modulename)
            return w_mod
        except executioncontext.OperationError,e:
            if not e.match(space, space.w_KeyError):
                raise
            w_mod = space.get_builtin_module(w_modulename)
            if w_mod is not None:
                space.setitem(space.w_modules,w_modulename,w_mod)
                return w_mod

            import os, __future__
            for path in space.unwrap(space.getattr(space.w_sys, w('path'))):
                f = os.path.join(path, space.unwrap(w_modulename) + '.py')
                if os.path.exists(f):
                    w_mod = space.newmodule(w_modulename)
                    space.setitem(space.w_modules, w_modulename, w_mod)
                    space.setattr(w_mod, w('__file__'), w(f))
                    w_source = w(open(f, 'r').read())
                    # wrt the __future__.generators.compiler_flag, "um" -- mwh
                    w_code = self.compile(w_source, w(f), w('exec'),
                                          w(__future__.generators.compiler_flag))
                    w_dict = space.getattr(w_mod, w('__dict__'))
                    space.unwrap(w_code).eval_code(space, w_dict, w_dict)

                    return w_mod
            
            w_exc = space.call_function(space.w_ImportError, w_modulename)
            raise executioncontext.OperationError(
                      space.w_ImportError, w_exc)
    __import__ = appmethod(__import__)

    def compile(self, w_str, w_filename, w_startstr,
                w_supplied_flags=None, w_dont_inherit=None):
        space = self.space
        str = space.unwrap(w_str)
        filename = space.unwrap(w_filename)
        startstr = space.unwrap(w_startstr)
        if w_supplied_flags is None:
            supplied_flags = 0
        else:
            supplied_flags = space.unwrap(w_supplied_flags)
            if supplied_flags is None:
                supplied_flags = 0
        if w_dont_inherit is None:
            dont_inherit = 0
        else:
            dont_inherit = space.unwrap(w_dont_inherit)
            if dont_inherit is None:
                dont_inherit = 0

        #print (str, filename, startstr, supplied_flags, dont_inherit)
        c = _b.compile(str, filename, startstr, supplied_flags, dont_inherit)
        res = pycode.PyByteCode()
        res._from_code(c)
        return space.wrap(res)
    compile = appmethod(compile)


    ####essentially implemented by the objectspace
    def abs(self, w_val):
        return self.space.abs(w_val)
    abs = appmethod(abs)

    def chr(self, w_ascii):
        w_character = self.space.newstring([w_ascii])
        return w_character
    chr = appmethod(chr)

    def len(self, w_obj):
        return self.space.len(w_obj)
    len = appmethod(len)

    def delattr(self, w_object, w_name):
        return self.space.delattr(w_object, w_name)
    delattr = appmethod(delattr)


    def getattr(self, w_object, w_name):
        return self.space.getattr(w_object, w_name)
    getattr = appmethod(getattr)


    def hash(self, w_object):
        return self.space.hash(w_object)
    hash = appmethod(hash)

    def oct(self, w_val):
        return self.space.oct(w_val)
    oct = appmethod(oct)


    def hex(self, w_val):
        return self.space.hex(w_val)
    hex = appmethod(hex)


    def id(self, w_object):
        return self.space.id(w_object)
    id = appmethod(id)

    #XXX
    #It works only for new-style classes.
    #So we have to fix it, when we add support for
    #the old-style classes
    def issubclass(self, w_cls1, w_cls2):
        return self.space.issubtype(w_cls1, w_cls2)
    issubclass = appmethod(issubclass)

    #XXX the is also the second form of iter, we don't have implemented
    def iter(self, w_collection):
        return self.space.iter(w_collection)
    iter = appmethod(iter)

    def ord(self, w_val):
        return self.space.ord(w_val)
    ord = appmethod(ord)


    def pow(self, w_val):
        return self.space.pow(w_val)
    pow = appmethod(pow)


    def repr(self, w_object):
        return self.space.repr(w_object)
    repr = appmethod(repr)


    def setattr(self, w_object, w_name, w_val):
        return self.space.setattr(w_object, w_name, w_val)
    setattr = appmethod(setattr)

    #XXX
    #We don't have newunicode at the time
    def unichr(self, w_val):
        return self.space.newunicode([w_val])
    unichr = appmethod(unichr)


    # we have None! But leave these at the bottom, otherwise the default
    # arguments of the above-defined functions will see this new None...
    None = appdata(_b.None)
##    False = appdata(_b.False)
##    True = appdata(_b.True)
##    dict = appdata(_b.dict)   # XXX temporary
##    tuple = appdata(_b.tuple) # XXX temporary
##    int = appdata(_b.int) # XXX temporary

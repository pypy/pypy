from __future__ import nested_scopes
from pypy.objspace.std.objspace import *
import pypy.interpreter.pyframe


class W_FuncObject(object):
    def __init__(w_self, w_code, w_globals, w_defaultarguments, w_closure):
        w_self.w_code = w_code
        w_self.w_globals = w_globals
        w_self.w_defaultarguments = w_defaultarguments
        w_self.w_closure = w_closure


def function_unwrap(space, w_function):
    # XXX this is probably a temporary hack
    def proxy_function(*args, **kw):
        w_arguments = space.wrap(args)
        w_keywords  = space.wrap(kw)
        w_result = func_call(space, w_function, w_arguments, w_keywords)
        return space.unwrap(w_result)
    # XXX no closure implemented
    return proxy_function

StdObjSpace.unwrap.register(function_unwrap, W_FuncObject)


def func_call(space, w_function, w_arguments, w_keywords):
    somecode = space.unwrap(w_function.w_code)
    w_globals = w_function.w_globals
    w_locals = somecode.build_arguments(space, w_arguments, w_keywords,
                  w_defaults = w_function.w_defaultarguments,
                  w_closure = w_function.w_closure)
    w_ret = somecode.eval_code(space, w_globals, w_locals)
    return w_ret

StdObjSpace.call.register(func_call, W_FuncObject, W_ANY, W_ANY)

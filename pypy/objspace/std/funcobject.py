from __future__ import nested_scopes
from pypy.objspace.std.objspace import *
from functype import W_FuncType
import pypy.interpreter.pyframe
from pypy.objspace.std.instmethobject import W_InstMethObject


class W_FuncObject(W_Object):
    statictype = W_FuncType

    def __init__(w_self, space, code, w_globals, w_defaultarguments, w_closure):
        W_Object.__init__(w_self, space)
        w_self.code = code
        w_self.w_globals = w_globals
        w_self.w_defaultarguments = w_defaultarguments
        w_self.w_closure = w_closure


registerimplementation(W_FuncObject)


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
    somecode = w_function.code
    w_globals = w_function.w_globals
    w_locals = somecode.build_arguments(space, w_arguments, w_keywords,
                  w_defaults = w_function.w_defaultarguments,
                  w_closure = w_function.w_closure)
    w_ret = somecode.eval_code(space, w_globals, w_locals)
    return w_ret

StdObjSpace.call.register(func_call, W_FuncObject, W_ANY, W_ANY)


def func_get(space, w_function, w_instance, w_cls):
    return W_InstMethObject(space, w_instance, w_function)

StdObjSpace.get.register(func_get, W_FuncObject, W_ANY, W_ANY)

def func_getattr(space, w_function, w_attr):
    if space.is_true(space.eq(w_attr, space.wrap('func_code'))):
        return space.wrap(w_function.code)
    else:
        raise FailedToImplement

StdObjSpace.getattr.register(func_getattr, W_FuncObject, W_ANY)

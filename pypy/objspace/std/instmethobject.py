from __future__ import nested_scopes
from pypy.objspace.std.objspace import *
from instmethtype import W_InstMethType


class W_InstMethObject(W_Object):
    statictype = W_InstMethType
    
    def __init__(w_self, space, w_im_self, w_im_func):
        W_Object.__init__(w_self, space)
        w_self.w_im_self = w_im_self
        w_self.w_im_func = w_im_func


registerimplementation(W_InstMethObject)


#def function_unwrap(space, w_function):
#    # XXX this is probably a temporary hack
#    def proxy_function(*args, **kw):
#        w_arguments = space.wrap(args)
#        w_keywords  = space.wrap(kw)
#        w_result = func_call(space, w_function, w_arguments, w_keywords)
#        return space.unwrap(w_result)
#    # XXX no closure implemented
#    return proxy_function
#
#StdObjSpace.unwrap.register(function_unwrap, W_FuncObject)


def call__InstMeth_ANY_ANY(space, w_instmeth, w_arguments, w_keywords):
    w_args = space.add(space.newtuple([w_instmeth.w_im_self]),
                       w_arguments)
    w_ret = space.call(w_instmeth.w_im_func, w_args, w_keywords)
    return w_ret

# XXX do __get__ for instance methods

register_all(vars())

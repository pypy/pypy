"""
Reviewed 03-06-21
This object should implement both bound and unbound methods.
Currently, the bound methods work:
__call__   tested, OK.

Unbound methods do not work yet (test is broken) at least in
application space.  Changing this module to make them work
would be easy: test in call__InstMeth_ANY_ANY if w_instmeth
is None; if so, insert nothing in the arguments, but rather
perform a typetest on the first argument.  However, this would
not be testable until getattr on a typeobject will return an
unbound-method, which, so far, it doesn't yet.
"""

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

def call__InstMeth_ANY_ANY(space, w_instmeth, w_arguments, w_keywords):
    w_args = space.add(space.newtuple([w_instmeth.w_im_self]),
                       w_arguments)
    w_ret = space.call(w_instmeth.w_im_func, w_args, w_keywords)
    return w_ret

# XXX do __get__ for instance methods

register_all(vars())

from pypy.objspace.std.objspace import *
from booltype import W_BoolType


class W_BoolObject(W_Object):
    delegate_once = {}
    statictype = W_BoolType

    def __init__(w_self, space, boolval):# please pass in a real bool, not an int
        W_Object.__init__(w_self, space)
        w_self.boolval = boolval

    def __eq__(w_self, w_other):
        "Implements 'is'."
        # all w_False wrapped values are equal ('is'-identical)
        # and so do all w_True wrapped values
        return (isinstance(w_other, W_BoolObject) and
                w_self.boolval == w_other.boolval)

    def __nonzero__(self):
        raise Exception, "you cannot do that, you must use space.is_true()"


def bool_is_true(space, w_bool):
    return w_bool.boolval

StdObjSpace.is_true.register(bool_is_true, W_BoolObject)
StdObjSpace.unwrap. register(bool_is_true, W_BoolObject)

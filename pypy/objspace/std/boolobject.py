from pypy.objspace.std.objspace import *
from booltype import W_BoolType
import intobject


class W_BoolObject(W_Object):
    statictype = W_BoolType

    def __init__(w_self, space, boolval):# please pass in a real bool, not an int
        W_Object.__init__(w_self, space)
        w_self.boolval = boolval

    def __nonzero__(w_self):
        raise Exception, "you cannot do that, you must use space.is_true()"


registerimplementation(W_BoolObject)

# bool-to-int delegation requires translating the .boolvar attribute
# to an .intval one
def bool_to_int(space, w_bool):
    return intobject.W_IntObject(space, int(w_bool.boolval))

W_BoolObject.delegate_once[intobject.W_IntObject] = bool_to_int


def bool_is_true(space, w_bool):
    return w_bool.boolval

StdObjSpace.is_true.register(bool_is_true, W_BoolObject)
StdObjSpace.unwrap. register(bool_is_true, W_BoolObject)

def bool_repr(space, w_bool):
    if w_bool.boolval:
        return space.wrap('True')
    else:
        return space.wrap('False')

StdObjSpace.repr.register(bool_repr, W_BoolObject)
        

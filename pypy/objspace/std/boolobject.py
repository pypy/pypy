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
def delegate__Bool(space, w_bool):
    return intobject.W_IntObject(space, int(w_bool.boolval))
delegate__Bool.priority = PRIORITY_PARENT_TYPE


def is_true__Bool(space, w_bool):
    return w_bool.boolval

def unwrap__Bool(space, w_bool):
    return w_bool.boolval

def repr__Bool(space, w_bool):
    if w_bool.boolval:
        return space.wrap('True')
    else:
        return space.wrap('False')


register_all(vars())

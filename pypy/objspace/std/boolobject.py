from pypy.objspace.std.objspace import *
from pypy.objspace.std import intobject


class W_BoolObject(W_Object):
    from pypy.objspace.std.booltype import bool_typedef as typedef

    def __init__(w_self, space, boolval):
        W_Object.__init__(w_self, space)
        w_self.boolval = not not boolval

    def __nonzero__(w_self):
        raise Exception, "you cannot do that, you must use space.is_true()"

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%s)" % (w_self.__class__.__name__, w_self.boolval)

    def unwrap(w_self):
        return w_self.boolval

registerimplementation(W_BoolObject)

# bool-to-int delegation requires translating the .boolvar attribute
# to an .intval one
def delegate_Bool2Int(w_bool):
    return intobject.W_IntObject(w_bool.space, int(w_bool.boolval))


def nonzero__Bool(space, w_bool):
    return w_bool

def repr__Bool(space, w_bool):
    if w_bool.boolval:
        return space.wrap('True')
    else:
        return space.wrap('False')

def and__Bool_Bool(space, w_bool1, w_bool2):
    return space.newbool(w_bool1.boolval & w_bool2.boolval)

def or__Bool_Bool(space, w_bool1, w_bool2):
    return space.newbool(w_bool1.boolval | w_bool2.boolval)

def xor__Bool_Bool(space, w_bool1, w_bool2):
    return space.newbool(w_bool1.boolval ^ w_bool2.boolval)

str__Bool = repr__Bool

register_all(vars())

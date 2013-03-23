from rpython.rlib.rbigint import rbigint
from rpython.rlib.rarithmetic import r_uint
from pypy.interpreter.error import OperationError
from pypy.objspace.std import newformat
from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.intobject import W_IntObject

class W_BoolObject(W_Object):
    from pypy.objspace.std.booltype import bool_typedef as typedef
    _immutable_fields_ = ['boolval']

    def __init__(self, boolval):
        self.boolval = not not boolval

    def __nonzero__(self):
        raise Exception("you cannot do that, you must use space.is_true()")

    def __repr__(self):
        """ representation for debugging purposes """
        return "%s(%s)" % (self.__class__.__name__, self.boolval)

    def unwrap(self, space):
        return self.boolval

    def int_w(self, space):
        return int(self.boolval)

    def uint_w(self, space):
        intval = int(self.boolval)
        return r_uint(intval)

    def bigint_w(self, space):
        return rbigint.fromint(int(self.boolval))

    def float_w(self, space):
        return float(self.boolval)

    def int(self, space):
        return self

registerimplementation(W_BoolObject)

W_BoolObject.w_False = W_BoolObject(False)
W_BoolObject.w_True  = W_BoolObject(True)

# bool-to-int delegation requires translating the .boolvar attribute
# to an .intval one
def delegate_Bool2IntObject(space, w_bool):
    return W_IntObject(int(w_bool.boolval))

def delegate_Bool2SmallInt(space, w_bool):
    from pypy.objspace.std.smallintobject import W_SmallIntObject
    return W_SmallIntObject(int(w_bool.boolval))   # cannot overflow


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

def format__Bool_ANY(space, w_bool, w_format_spec):
    return newformat.run_formatter(
            space, w_format_spec, "format_int_or_long", w_bool,
            newformat.INT_KIND)

register_all(vars())

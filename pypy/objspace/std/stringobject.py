from objspace import *
from intobject   import W_IntObject
from sliceobject import W_SliceObject

applicationfile = StdObjSpace.AppFile(__name__)

class W_StringObject:
    def __init__(w_self, str):
        w_self.value = str
    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%r)" % (w_self.__class__.__name__, w_self.value)
    def nonzero(w_self):
        return W_IntObject(w_self.value != 0)
    def hash(w_self):
        return W_IntObject(hash(self.value))


def str_unwrap(space, w_str):
    return w_str.value

StdObjSpace.unwrap.register(str_unwrap, W_StringObject)

def str_str_compare(space, w_str1, w_str2, op):
    i = w_str1.value
    j = w_str2.value
    if   op == '<':  return space.newbool( i < j  )
    elif op == '<=': return space.newbool( i <= j )
    elif op == '==': return space.newbool( i == j )
    elif op == '!=': return space.newbool( i != j )
    elif op == '>':  return space.newbool( i > j  )
    elif op == '>=': return space.newbool( i >= j )
    #elif op == 'in':           # n.a.
    #elif op == 'not in':       # n.a.
    #elip op == 'is': is_,      # elsewhere
    #elif op == 'is not':       # elsewhere
    #elif op == 'exc match':    # exceptions
    else:
        msg = 'string comparison "%s" not implemented' % op
        raise FailedToImplement(space.w_TypeError,
                                space.wrap(msg))

StdObjSpace.compare.register(str_str_compare, W_StringObject, W_StringObject)

def getitem_str_int(space, w_str, w_int):
    return W_StringObject(w_str.value[w_int.intval])

StdObjSpace.getitem.register(getitem_str_int, 
                                W_StringObject, W_IntObject)

def getitem_str_slice(space, w_str, w_slice):
    return applicationfile.call(space, "getitem_string_slice", [w_str, w_slice])

StdObjSpace.getitem.register(getitem_str_slice, 
                                W_StringObject, W_SliceObject)

def add_str_str(space, w_left, w_right):
    return W_StringObject(w_left.value + w_right.value)

StdObjSpace.getitem.register(add_str_str, W_StringObject, W_StringObject)

def mod_str_ANY(space, w_left, w_right):
    notImplemented
 
def mod_str_tuple(space, w_format, w_args):
    notImplemented

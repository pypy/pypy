from pypy.interpreter.error import OperationError
from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.inttype import wrapint
from pypy.objspace.std.multimethod import FailedToImplement
from pypy.rlib.rarithmetic import intmask
from pypy.objspace.std.sliceobject import W_SliceObject, normalize_simple_slice
from pypy.objspace.std import slicetype
from pypy.interpreter import gateway
from pypy.rlib.debug import make_sure_not_resized
from pypy.objspace.std.tupleobject import W_TupleObject

class W_SmallTupleObject(W_Object):
    from pypy.objspace.std.tupletype import tuple_typedef as typedef

    def tolist(self):
        raise NotImplementedError

    def length(self):
        raise NotImplementedError

class W_SmallTupleObject2(W_SmallTupleObject):

    def __init__(self, w_value01, w_value02):
        self.w_value01 = w_value01
        self.w_value02 = w_value02

    def tolist(self):
        return [self.w_value01, self.w_value02]

    def length(self):
        return 2

    def getitem(self, index):
        if index == 0:
            return self.w_value01
        elif index == 1:
            return self.w_value02
        else:
            raise IndexError

registerimplementation(W_SmallTupleObject)

def delegate_SmallTuple2Tuple(space, w_small):
    return W_TupleObject([w_small.w_value01, w_small.w_value02])

def len__SmallTuple(space, w_tuple):
    return space.wrap(w_tuple.length())

def getitem__SmallTuple_ANY(space, w_tuple, w_index):
    index = space.getindex_w(w_index, space.w_IndexError, "tuple index")
    if index < 0:
        index += w_tuple.length()
    try:
        return w_tuple.getitem(index)
    except IndexError:
        raise OperationError(space.w_IndexError,
                             space.wrap("tuple index out of range"))

from pypy.objspace.std import tupletype
register_all(vars(), tupletype)

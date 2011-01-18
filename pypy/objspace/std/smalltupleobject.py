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
from pypy.rlib.unroll import unrolling_iterable
from pypy.objspace.std.tupleobject import W_TupleObject

class W_SmallTupleObject(W_Object):
    from pypy.objspace.std.tupletype import tuple_typedef as typedef

    def tolist(self):
        raise NotImplementedError

    def length(self):
        raise NotImplementedError

def make_specialized_class(n):
    iter_n = unrolling_iterable(range(n))
    class cls(W_SmallTupleObject):

        def __init__(self, *values):
            for i in iter_n:
                setattr(self, 'w_value%s' % i, values[i])

        def tolist(self):
            l = [None] * n
            for i in iter_n:
                l[i] = getattr(self, 'w_value%s' % i)
            return l

        def length(self):
            return n

        def getitem(self, index):
            for i in iter_n:
                if index == i:
                    return getattr(self,'w_value%s' % i)
            raise IndexError

    cls.__name__ = "W_SmallTupleObject%s" % n
    return cls

W_SmallTupleObject2 = make_specialized_class(2)

registerimplementation(W_SmallTupleObject)

def delegate_SmallTuple2Tuple(space, w_small):
    return W_TupleObject(w_small.tolist())

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

def getitem__SmallTuple_Slice(space, w_tuple, w_slice):
    length = w_tuple.length()
    start, stop, step, slicelength = w_slice.indices4(space, length)
    assert slicelength >= 0
    subitems = [None] * slicelength
    for i in range(slicelength):
        subitems[i] = w_tuple.getitem(start)
        start += step
    return space.newtuple(subitems)

from pypy.objspace.std import tupletype
register_all(vars(), tupletype)

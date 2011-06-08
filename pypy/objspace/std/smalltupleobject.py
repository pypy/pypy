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

    def getitem(self, index):
        raise NotImplementedError

    def hash(self, space):
        raise NotImplementedError

    def eq(self, space, w_other):
        raise NotImplementedError

    def setitem(self, index, w_item):
        raise NotImplementedError

    def unwrap(w_tuple, space):
        items = [space.unwrap(w_item) for w_item in w_tuple.tolist()]
        return tuple(items)

def make_specialized_class(n):
    iter_n = unrolling_iterable(range(n))
    class cls(W_SmallTupleObject):

        def __init__(self, values):
            assert len(values) == n
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

        def setitem(self, index, w_item):
            for i in iter_n:
                if index == i:
                    setattr(self, 'w_value%s' % i, w_item)
                    return
            raise IndexError

        def eq(self, space, w_other):
            if self.length() != w_other.length():
                return space.w_False
            for i in iter_n:
                item1 = self.getitem(i)
                item2 = w_other.getitem(i)
                if not space.eq_w(item1, item2):
                    return space.w_False
            return space.w_True

        def hash(self, space):
            mult = 1000003
            x = 0x345678
            z = self.length()
            for i in iter_n:
                w_item = self.getitem(i)
                y = space.int_w(space.hash(w_item))
                x = (x ^ y) * mult
                z -= 1
                mult += 82520 + z + z
            x += 97531
            return space.wrap(intmask(x))

    cls.__name__ = "W_SmallTupleObject%s" % n
    return cls

W_SmallTupleObject2 = make_specialized_class(2)
W_SmallTupleObject3 = make_specialized_class(3)
W_SmallTupleObject4 = make_specialized_class(4)
W_SmallTupleObject5 = make_specialized_class(5)
W_SmallTupleObject6 = make_specialized_class(6)
W_SmallTupleObject7 = make_specialized_class(7)
W_SmallTupleObject8 = make_specialized_class(8)

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

def mul_smalltuple_times(space, w_tuple, w_times):
    try:
        times = space.getindex_w(w_times, space.w_OverflowError)
    except OperationError, e:
        if e.match(space, space.w_TypeError):
            raise FailedToImplement
        raise
    if times == 1 and space.type(w_tuple) == space.w_tuple:
        return w_tuple
    items = w_tuple.tolist()
    return space.newtuple(items * times)

def mul__SmallTuple_ANY(space, w_tuple, w_times):
    return mul_smalltuple_times(space, w_tuple, w_times)

def mul__ANY_SmallTuple(space, w_times, w_tuple):
    return mul_smalltuple_times(space, w_tuple, w_times)

def eq__SmallTuple_SmallTuple(space, w_tuple1, w_tuple2):
    return w_tuple1.eq(space, w_tuple2)

def hash__SmallTuple(space, w_tuple):
    return w_tuple.hash(space)

from pypy.objspace.std import tupletype
register_all(vars(), tupletype)

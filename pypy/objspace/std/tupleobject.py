from pypy.objspace.std.objspace import *
from tupletype import W_TupleType
from intobject import W_IntObject
from sliceobject import W_SliceObject


class W_TupleObject(W_Object):
    statictype = W_TupleType

    def __init__(w_self, space, wrappeditems):
        W_Object.__init__(w_self, space)
        w_self.wrappeditems = wrappeditems   # a list of wrapped values

    def __repr__(w_self):
        """ representation for debugging purposes """
        reprlist = [repr(w_item) for w_item in w_self.wrappeditems]
        return "%s(%s)" % (w_self.__class__.__name__, ', '.join(reprlist))


registerimplementation(W_TupleObject)


def unwrap__Tuple(space, w_tuple):
    items = [space.unwrap(w_item) for w_item in w_tuple.wrappeditems]
    return tuple(items)

def len__Tuple(space, w_tuple):
    result = len(w_tuple.wrappeditems)
    return W_IntObject(space, result)

def getitem__Tuple_Int(space, w_tuple, w_index):
    items = w_tuple.wrappeditems
    try:
        w_item = items[w_index.intval]
    except IndexError:
        raise OperationError(space.w_IndexError,
                             space.wrap("tuple index out of range"))
    return w_item

def getitem__Tuple_Slice(space, w_tuple, w_slice):
    items = w_tuple.wrappeditems
    w_length = space.wrap(len(items))
    w_start, w_stop, w_step, w_slicelength = w_slice.indices(w_length)
    start       = space.unwrap(w_start)
    step        = space.unwrap(w_step)
    slicelength = space.unwrap(w_slicelength)
    assert slicelength >= 0
    subitems = [None] * slicelength
    for i in range(slicelength):
        subitems[i] = items[start]
        start += step
    return W_TupleObject(space, subitems)

def iter__Tuple(space, w_tuple):
    import iterobject
    return iterobject.W_SeqIterObject(space, w_tuple)

def add__Tuple_Tuple(space, w_tuple1, w_tuple2):
    items1 = w_tuple1.wrappeditems
    items2 = w_tuple2.wrappeditems
    return W_TupleObject(space, items1 + items2)

def mul__Tuple_Int(space, w_tuple, w_int):
    items = w_tuple.wrappeditems
    times = w_int.intval
    return W_TupleObject(space, items * times)


def mul__Int_Tuple(space, w_int, w_tuple):
    return mul__Tuple_Int(space, w_tuple, w_int)

def ne__Tuple_Tuple(space, w_tuple1, w_tuple2):
    return space.not_(eq__Tuple_Tuple(space, w_tuple1, w_tuple2))

def eq__Tuple_Tuple(space, w_tuple1, w_tuple2):
    items1 = w_tuple1.wrappeditems
    items2 = w_tuple2.wrappeditems
    if len(items1) != len(items2):
        return space.w_False
    for item1, item2 in zip(items1, items2):
        if not space.is_true(space.eq(item1, item2)):
            return space.w_False
    return space.w_True

def _min(a, b):
    if a < b:
        return a
    return b

def lt__Tuple_Tuple(space, w_tuple1, w_tuple2):
    items1 = w_tuple1.wrappeditems
    items2 = w_tuple2.wrappeditems
    ncmp = _min(len(items1), len(items2))
    # Search for the first index where items are different
    for p in range(ncmp):
        if not space.is_true(space.eq(items1[p], items2[p])):
            return space.lt(items1[p], items2[p])
    # No more items to compare -- compare sizes
    return space.newbool(len(items1) < len(items2))

def ge__Tuple_Tuple(space, w_tuple1, w_tuple2):
    return space.not_(lt__Tuple_Tuple(space, w_tuple1, w_tuple2))

def gt__Tuple_Tuple(space, w_tuple1, w_tuple2):
    items1 = w_tuple1.wrappeditems
    items2 = w_tuple2.wrappeditems
    ncmp = _min(len(items1), len(items2))
    # Search for the first index where items are different
    for p in range(ncmp):
        if not space.is_true(space.eq(items1[p], items2[p])):
            return space.gt(items1[p], items2[p])
    # No more items to compare -- compare sizes
    return space.newbool(len(items1) > len(items2))

def le__Tuple_Tuple(space, w_tuple1, w_tuple2):
    return space.not_(gt__Tuple_Tuple(space, w_tuple1, w_tuple2))

def repr__Tuple(space, w_tuple):
    # XXX slimy! --mwh
    return space.wrap(repr(space.unwrap(w_tuple)))


register_all(vars())

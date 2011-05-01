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

class W_TupleObject(W_Object):
    from pypy.objspace.std.tupletype import tuple_typedef as typedef
    _immutable_fields_ = ['wrappeditems[*]']

    def __init__(w_self, wrappeditems):
        make_sure_not_resized(wrappeditems)
        w_self.wrappeditems = wrappeditems   # a list of wrapped values

    def __repr__(w_self):
        """ representation for debugging purposes """
        reprlist = [repr(w_item) for w_item in w_self.wrappeditems]
        return "%s(%s)" % (w_self.__class__.__name__, ', '.join(reprlist))

    def unwrap(w_tuple, space):
        items = [space.unwrap(w_item) for w_item in w_tuple.wrappeditems] # XXX generic mixed types unwrap
        return tuple(items)

registerimplementation(W_TupleObject)


def len__Tuple(space, w_tuple):
    result = len(w_tuple.wrappeditems)
    return wrapint(space, result)

def getitem__Tuple_ANY(space, w_tuple, w_index):
    # getindex_w should get a second argument space.w_IndexError,
    # but that doesn't exist the first time this is called.
    try:
        w_IndexError = space.w_IndexError
    except AttributeError:
        w_IndexError = None
    index = space.getindex_w(w_index, w_IndexError, "tuple index")
    try:
        return w_tuple.wrappeditems[index]
    except IndexError:
        raise OperationError(space.w_IndexError,
                             space.wrap("tuple index out of range"))

def getitem__Tuple_Slice(space, w_tuple, w_slice):
    items = w_tuple.wrappeditems
    length = len(items)
    start, stop, step, slicelength = w_slice.indices4(space, length)
    assert slicelength >= 0
    subitems = [None] * slicelength
    for i in range(slicelength):
        subitems[i] = items[start]
        start += step
    return W_TupleObject(subitems)

def getslice__Tuple_ANY_ANY(space, w_tuple, w_start, w_stop):
    length = len(w_tuple.wrappeditems)
    start, stop = normalize_simple_slice(space, length, w_start, w_stop)
    return W_TupleObject(w_tuple.wrappeditems[start:stop])

def contains__Tuple_ANY(space, w_tuple, w_obj):
    for w_item in w_tuple.wrappeditems:
        if space.eq_w(w_item, w_obj):
            return space.w_True
    return space.w_False

def iter__Tuple(space, w_tuple):
    from pypy.objspace.std import iterobject
    return iterobject.W_FastTupleIterObject(w_tuple, w_tuple.wrappeditems)

def add__Tuple_Tuple(space, w_tuple1, w_tuple2):
    items1 = w_tuple1.wrappeditems
    items2 = w_tuple2.wrappeditems
    return W_TupleObject(items1 + items2)

def mul_tuple_times(space, w_tuple, w_times):
    try:
        times = space.getindex_w(w_times, space.w_OverflowError)
    except OperationError, e:
        if e.match(space, space.w_TypeError):
            raise FailedToImplement
        raise
    if times == 1 and space.type(w_tuple) == space.w_tuple:
        return w_tuple
    items = w_tuple.wrappeditems
    return W_TupleObject(items * times)

def mul__Tuple_ANY(space, w_tuple, w_times):
    return mul_tuple_times(space, w_tuple, w_times)

def mul__ANY_Tuple(space, w_times, w_tuple):
    return mul_tuple_times(space, w_tuple, w_times)

def eq__Tuple_Tuple(space, w_tuple1, w_tuple2):
    items1 = w_tuple1.wrappeditems
    items2 = w_tuple2.wrappeditems
    if len(items1) != len(items2):
        return space.w_False
    for i in range(len(items1)):
        item1 = items1[i]
        item2 = items2[i]
        if not space.eq_w(item1, item2):
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
        if not space.eq_w(items1[p], items2[p]):
            return space.lt(items1[p], items2[p])
    # No more items to compare -- compare sizes
    return space.newbool(len(items1) < len(items2))

def gt__Tuple_Tuple(space, w_tuple1, w_tuple2):
    items1 = w_tuple1.wrappeditems
    items2 = w_tuple2.wrappeditems
    ncmp = _min(len(items1), len(items2))
    # Search for the first index where items are different
    for p in range(ncmp):
        if not space.eq_w(items1[p], items2[p]):
            return space.gt(items1[p], items2[p])
    # No more items to compare -- compare sizes
    return space.newbool(len(items1) > len(items2))

def repr__Tuple(space, w_tuple):
    items = w_tuple.wrappeditems
    # XXX this is quite innefficient, still better than calling
    #     it via applevel
    if len(items) == 1:
        return space.wrap("(" + space.str_w(space.repr(items[0])) + ",)")
    return space.wrap("(" +
                 (", ".join([space.str_w(space.repr(item)) for item in items]))
                      + ")")

def hash__Tuple(space, w_tuple):
    return space.wrap(hash_tuple(space, w_tuple.wrappeditems))

def hash_tuple(space, wrappeditems):
    # this is the CPython 2.4 algorithm (changed from 2.3)
    mult = 1000003
    x = 0x345678
    z = len(wrappeditems)
    for w_item in wrappeditems:
        y = space.int_w(space.hash(w_item))
        x = (x ^ y) * mult
        z -= 1
        mult += 82520 + z + z
    x += 97531
    return intmask(x)

def getnewargs__Tuple(space, w_tuple):
    return space.newtuple([W_TupleObject(w_tuple.wrappeditems)])

def tuple_count__Tuple_ANY(space, w_tuple, w_obj):
    count = 0
    for w_item in w_tuple.wrappeditems:
        if space.eq_w(w_item, w_obj):
            count += 1
    return space.wrap(count)

def tuple_index__Tuple_ANY_ANY_ANY(space, w_tuple, w_obj, w_start, w_stop):
    start = slicetype._Eval_SliceIndex(space, w_start)
    stop = slicetype._Eval_SliceIndex(space, w_stop)
    length = len(w_tuple.wrappeditems)
    if start < 0:
        start += length
        if start < 0:
            start = 0
    if stop < 0:
        stop += length
        if stop < 0:
            stop = 0
    for i in range(start, min(stop, length)):
        w_item = w_tuple.wrappeditems[i]
        if space.eq_w(w_item, w_obj):
            return space.wrap(i)
    raise OperationError(space.w_ValueError,
                         space.wrap("tuple.index(x): x not in tuple"))

from pypy.objspace.std import tupletype
register_all(vars(), tupletype)

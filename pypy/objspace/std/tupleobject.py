from pypy.objspace.std.objspace import *
from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.restricted_int import intmask
from pypy.objspace.std.sliceobject import W_SliceObject
from pypy.objspace.std import slicetype
from pypy.interpreter import gateway

class W_TupleObject(W_Object):
    from pypy.objspace.std.tupletype import tuple_typedef as typedef
    
    def __init__(w_self, space, wrappeditems):
        W_Object.__init__(w_self, space)
        w_self.wrappeditems = wrappeditems   # a list of wrapped values

    def __repr__(w_self):
        """ representation for debugging purposes """
        reprlist = [repr(w_item) for w_item in w_self.wrappeditems]
        return "%s(%s)" % (w_self.__class__.__name__, ', '.join(reprlist))

    def unwrap(w_tuple):
        space = w_tuple.space
        items = [space.unwrap(w_item) for w_item in w_tuple.wrappeditems] # XXX generic mixed types unwrap
        return tuple(items)


registerimplementation(W_TupleObject)


def len__Tuple(space, w_tuple):
    result = len(w_tuple.wrappeditems)
    return W_IntObject(space, result)

def getitem__Tuple_ANY(space, w_tuple, w_index):
    items = w_tuple.wrappeditems
    try:
        w_item = items[space.int_w(w_index)]
    except IndexError:
        raise OperationError(space.w_IndexError,
                             space.wrap("tuple index out of range"))
    return w_item

def getitem__Tuple_Slice(space, w_tuple, w_slice):
    items = w_tuple.wrappeditems
    length = len(items)
    start, stop, step, slicelength = slicetype.indices4(space, w_slice, length)
    assert slicelength >= 0
    subitems = [None] * slicelength
    for i in range(slicelength):
        subitems[i] = items[start]
        start += step
    return W_TupleObject(space, subitems)

def contains__Tuple_ANY(space, w_tuple, w_obj):
    for w_item in w_tuple.wrappeditems:
        if space.eq_w(w_item, w_obj):
            return space.w_True
    return space.w_False

def iter__Tuple(space, w_tuple):
    from pypy.objspace.std import iterobject
    return iterobject.W_SeqIterObject(space, w_tuple)

def add__Tuple_Tuple(space, w_tuple1, w_tuple2):
    items1 = w_tuple1.wrappeditems
    items2 = w_tuple2.wrappeditems
    return W_TupleObject(space, items1 + items2)

def mul_tuple_times(space, w_tuple, times):
    items = w_tuple.wrappeditems
    return W_TupleObject(space, items * times)    

def mul__Tuple_ANY(space, w_tuple, w_times):
    return mul_tuple_times(space, w_tuple, space.int_w(w_times))

def mul__ANY_Tuple(space, w_times, w_tuple):
    return mul_tuple_times(space, w_tuple, space.int_w(w_times))

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

app = gateway.applevel("""
    def repr__Tuple(t):
        if len(t) == 1:
            return "(" + repr(t[0]) + ",)"
        else:
            return "(" + ", ".join([repr(x) for x in t]) + ')'
""") 

repr__Tuple = app.interphook('repr__Tuple') 

def hash__Tuple(space, w_tuple):
    # this is the CPython 2.4 algorithm (changed from 2.3)
    mult = 1000003
    x = 0x345678
    z = len(w_tuple.wrappeditems)
    for w_item in w_tuple.wrappeditems:
        y = space.int_w(space.hash(w_item))
        x = (x ^ y) * mult
        z -= 1
        mult += 82520 + z + z
    x += 97531
    return space.wrap(intmask(x))

register_all(vars())

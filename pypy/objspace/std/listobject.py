from pypy.objspace.std.objspace import *
from intobject import W_IntObject
from sliceobject import W_SliceObject
from instmethobject import W_InstMethObject


class W_ListObject(object):

    def __init__(self, wrappeditems):
        self.wrappeditems = wrappeditems   # a list of wrapped values

    def __repr__(w_self):
        """ representation for debugging purposes """
        reprlist = [repr(w_item) for w_item in w_self.wrappeditems]
        return "%s(%s)" % (w_self.__class__.__name__, ', '.join(reprlist))

###    def append(w_self):
###        .:.


def list_unwrap(space, w_list):
    items = [space.unwrap(w_item) for w_item in w_list.wrappeditems]
    return list(items)

StdObjSpace.unwrap.register(list_unwrap, W_ListObject)

def list_is_true(space, w_list):
    return not not w_list.wrappeditems

StdObjSpace.is_true.register(list_is_true, W_ListObject)

def list_len(space, w_list):
    result = len(w_list.wrappeditems)
    return W_IntObject(result)

StdObjSpace.len.register(list_len, W_ListObject)

def getitem_list_int(space, w_list, w_index):
    items = w_list.wrappeditems
    try:
        w_item = items[w_index.intval]
    except IndexError:
        raise OperationError(space.w_IndexError,
                             space.wrap("list index out of range"))
    return w_item

StdObjSpace.getitem.register(getitem_list_int, W_ListObject, W_IntObject)

def getitem_list_slice(space, w_list, w_slice):
    items = w_list.wrappeditems
    w_length = space.wrap(len(items))
    w_start, w_stop, w_step, w_slicelength = w_slice.indices(space, w_length)
    start       = space.unwrap(w_start)
    step        = space.unwrap(w_step)
    slicelength = space.unwrap(w_slicelength)
    assert slicelength >= 0
    subitems = [None] * slicelength
    for i in range(slicelength):
        subitems[i] = items[start]
        start += step
    return W_ListObject(subitems)

StdObjSpace.getitem.register(getitem_list_slice, W_ListObject, W_SliceObject)

def list_iter(space, w_list):
    import iterobject
    return iterobject.W_SeqIterObject(w_list)

StdObjSpace.iter.register(list_iter, W_ListObject)

def list_add(space, w_list1, w_list2):
    items1 = w_list1.wrappeditems
    items2 = w_list2.wrappeditems
    return W_ListObject(items1 + items2)

StdObjSpace.add.register(list_add, W_ListObject, W_ListObject)

def list_eq(space, w_list1, w_list2):
    items1 = w_list1.wrappeditems
    items2 = w_list2.wrappeditems
    if len(items1) != len(items2):
        return space.w_False
    for item1, item2 in zip(items1, items2):
        if not space.is_true(space.eq(item1, item2)):
            return space.w_False
    return space.w_True

StdObjSpace.eq.register(list_eq, W_ListObject, W_ListObject)

# upto here, lists are nearly identical to tuples.
# XXX have to add over-allocation!

###def getattr_list(space, w_list, w_attr):
###    if space.is_true(space.eq(w_attr, space.wrap('append'))):
###        ...
###        return W_InstMethObject(w_list, w_builtinfn)
###    raise FailedToImplement(space.w_AttributeError)

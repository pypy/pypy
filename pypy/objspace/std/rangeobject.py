from pypy.interpreter.error import OperationError
from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.multimethod import FailedToImplement
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.objspace.std.inttype import wrapint
from pypy.objspace.std.sliceobject import W_SliceObject, normalize_simple_slice
from pypy.objspace.std.listobject import W_ListObject
from pypy.objspace.std import listtype, iterobject, slicetype
from pypy.interpreter import gateway, baseobjspace

def length(start, stop, step):
    if step > 0:
        if stop <= start:
            return 0
        return (stop - start + step - 1)/step

    else:  # step must be < 0
        if stop >= start:
            return 0
        return (start - stop - step  - 1)/-step


class W_RangeListObject(W_Object):
    typedef = listtype.list_typedef

    def __init__(w_self, start, step, length):
        assert step != 0
        w_self.start = start
        w_self.step = step
        w_self.length = length
        w_self.w_list = None

    def force(w_self, space):
        if w_self.w_list is not None:
            return w_self.w_list
        start = w_self.start
        step = w_self.step
        length = w_self.length
        if not length:
            w_self.w_list = space.newlist([])
            return w_self.w_list

        arr = [None] * length  # this is to avoid using append.

        i = start
        n = 0
        while n < length:
            arr[n] = wrapint(space, i)
            i += step
            n += 1

        w_self.w_list = space.newlist(arr)
        return w_self.w_list

    def getitem(w_self, i):
        if i < 0:
            i += w_self.length
            if i < 0:
                raise IndexError
        elif i >= w_self.length:
            raise IndexError
        return w_self.start + i * w_self.step

    def getitem_unchecked(w_self, i):
        # bounds not checked, on purpose
        return w_self.start + i * w_self.step

    def __repr__(w_self):
        if w_self.w_list is None:
            return "W_RangeListObject(%s, %s, %s)" % (
                w_self.start, w_self.step, w_self.length)
        else:
            return "W_RangeListObject(%r)" % (w_self.w_list, )

def delegate_range2list(space, w_rangelist):
    return w_rangelist.force(space)

def len__RangeList(space, w_rangelist):
    if w_rangelist.w_list is not None:
        return space.len(w_rangelist.w_list)
    return wrapint(space, w_rangelist.length)


def getitem__RangeList_ANY(space, w_rangelist, w_index):
    if w_rangelist.w_list is not None:
        return space.getitem(w_rangelist.w_list, w_index)
    idx = space.getindex_w(w_index, space.w_IndexError, "list index")
    try:
        return wrapint(space, w_rangelist.getitem(idx))
    except IndexError:
        raise OperationError(space.w_IndexError,
                             space.wrap("list index out of range"))

def getitem__RangeList_Slice(space, w_rangelist, w_slice):
    if w_rangelist.w_list is not None:
        return space.getitem(w_rangelist.w_list, w_slice)
    length = w_rangelist.length
    start, stop, step, slicelength = w_slice.indices4(space, length)
    assert slicelength >= 0
    rangestart = w_rangelist.getitem_unchecked(start)
    rangestep = w_rangelist.step * step
    return W_RangeListObject(rangestart, rangestep, slicelength)

def getslice__RangeList_ANY_ANY(space, w_rangelist, w_start, w_stop):
    if w_rangelist.w_list is not None:
        return space.getslice(w_rangelist.w_list, w_start, w_stop)
    length = w_rangelist.length
    start, stop = normalize_simple_slice(space, length, w_start, w_stop)
    slicelength = stop - start
    assert slicelength >= 0
    rangestart = w_rangelist.getitem_unchecked(start)
    rangestep = w_rangelist.step
    return W_RangeListObject(rangestart, rangestep, slicelength)

def iter__RangeList(space, w_rangelist):
    return W_RangeIterObject(w_rangelist)

def repr__RangeList(space, w_rangelist):
    if w_rangelist.w_list is not None:
        return space.repr(w_rangelist.w_list)
    if w_rangelist.length == 0:
        return space.wrap('[]')
    result = [''] * w_rangelist.length
    i = w_rangelist.start
    n = 0
    while n < w_rangelist.length:
        result[n] = str(i)
        i += w_rangelist.step
        n += 1
    return space.wrap("[" + ", ".join(result) + "]")

def inplace_add__RangeList_ANY(space, w_rangelist, w_iterable2):
    space.inplace_add(w_rangelist.force(space), w_iterable2)
    return w_rangelist

def inplace_mul__RangeList_ANY(space, w_rangelist, w_number):
    space.inplace_mul(w_rangelist.force(space), w_number)
    return w_rangelist


def list_pop__RangeList_ANY(space, w_rangelist, w_idx=-1):
    if w_rangelist.w_list is not None:
        raise FailedToImplement
    length = w_rangelist.length
    if length == 0:
        raise OperationError(space.w_IndexError,
                             space.wrap("pop from empty list"))
    if space.isinstance_w(w_idx, space.w_float):
        raise OperationError(space.w_TypeError,
            space.wrap("integer argument expected, got float")
        )
    idx = space.int_w(space.int(w_idx))
    if idx == 0:
        result = w_rangelist.start
        w_rangelist.start += w_rangelist.step
        w_rangelist.length -= 1
        return wrapint(space, result)
    if idx == -1 or idx == length - 1:
        w_rangelist.length -= 1
        return wrapint(
            space, w_rangelist.start + (length - 1) * w_rangelist.step)
    if idx >= w_rangelist.length:
        raise OperationError(space.w_IndexError,
                             space.wrap("pop index out of range"))
    raise FailedToImplement

def list_reverse__RangeList(space, w_rangelist):
    # probably somewhat useless, but well...
    if w_rangelist.w_list is not None:
        raise FailedToImplement
    w_rangelist.start = w_rangelist.getitem_unchecked(w_rangelist.length-1)
    w_rangelist.step = -w_rangelist.step

def list_sort__RangeList_None_None_ANY(space, w_rangelist, w_cmp,
                                       w_keyfunc, w_reverse):
    # even more useless but fun
    has_reverse = space.is_true(w_reverse)
    if w_rangelist.w_list is not None:
        raise FailedToImplement
    if has_reverse:
        factor = -1
    else:
        factor = 1
    reverse = w_rangelist.step * factor < 0
    if reverse:
        w_rangelist.start = w_rangelist.getitem_unchecked(w_rangelist.length-1)
        w_rangelist.step = -w_rangelist.step
    return space.w_None


class W_RangeIterObject(iterobject.W_AbstractSeqIterObject):
    pass

def iter__RangeIter(space, w_rangeiter):
    return w_rangeiter

def next__RangeIter(space, w_rangeiter):
    w_rangelist = w_rangeiter.w_seq
    if w_rangelist is None:
        raise OperationError(space.w_StopIteration, space.w_None)
    assert isinstance(w_rangelist, W_RangeListObject)
    index = w_rangeiter.index
    if w_rangelist.w_list is not None:
        try:
            w_item = space.getitem(w_rangelist.w_list,
                                   wrapint(space, index))
        except OperationError, e:
            w_rangeiter.w_seq = None
            if not e.match(space, space.w_IndexError):
                raise
            raise OperationError(space.w_StopIteration, space.w_None)
    else:
        if index >= w_rangelist.length:
            w_rangeiter.w_seq = None
            raise OperationError(space.w_StopIteration, space.w_None)
        w_item = wrapint(
            space,
            w_rangelist.getitem_unchecked(index))
    w_rangeiter.index = index + 1
    return w_item

# XXX __length_hint__()
##def len__RangeIter(space,  w_rangeiter):
##    if w_rangeiter.w_seq is None:
##        return wrapint(space, 0)
##    index = w_rangeiter.index
##    w_length = space.len(w_rangeiter.w_seq)
##    w_len = space.sub(w_length, wrapint(space, index))
##    if space.is_true(space.lt(w_len, wrapint(space, 0))):
##        w_len = wrapint(space, 0)
##    return w_len

registerimplementation(W_RangeListObject)
registerimplementation(W_RangeIterObject)

register_all(vars(), listtype)

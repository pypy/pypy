from pypy.objspace.std.objspace import *
from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.sliceobject import W_SliceObject
from pypy.objspace.std.tupleobject import W_TupleObject

from pypy.objspace.std import slicetype
from pypy.interpreter import gateway, baseobjspace
from pypy.tool.rarithmetic import r_uint
from pypy.objspace.std.listsort import TimSort


class W_ListObject(W_Object):
    from pypy.objspace.std.listtype import list_typedef as typedef
    
    def __init__(w_self, space, wrappeditems):
        W_Object.__init__(w_self, space)
        w_self.ob_item = []
        w_self.ob_size = 0
        newlen = len(wrappeditems)
        _list_resize(w_self, newlen)
        w_self.ob_size = newlen
        items = w_self.ob_item
        p = newlen
        while p:
            p -= 1
            items[p] = wrappeditems[p]

    def __repr__(w_self):
        """ representation for debugging purposes """
        reprlist = [repr(w_item) for w_item in w_self.ob_item[:w_self.ob_size]]
        return "%s(%s)" % (w_self.__class__.__name__, ', '.join(reprlist))

    def unwrap(w_list):
        space = w_list.space
        items = [space.unwrap(w_item) for w_item in w_list.ob_item[:w_list.ob_size]]# XXX generic mixed types unwrap
        return list(items)

    def clear(w_list):
        w_list.ob_item = []
        w_list.ob_size = 0


registerimplementation(W_ListObject)


def init__List(space, w_list, __args__):
    w_iterable, = __args__.parse('list',
                               (['sequence'], None, None),   # signature
                               [W_ListObject(space, [])])    # default argument
    w_list.clear()

    length = 0
    try:
        length = space.int_w(space.len(w_iterable))
        if length < 0:
            length = 8 
    except OperationError, e:
        pass # for now
    _list_resize(w_list, length)
    w_iterator = space.iter(w_iterable)
    while True:
        try:
            w_item = space.next(w_iterator)
        except OperationError, e:
            if not e.match(space, space.w_StopIteration):
                raise
            break  # done
        _ins1(w_list, w_list.ob_size, w_item)


def len__List(space, w_list):
    result = w_list.ob_size
    return W_IntObject(space, result)

def getitem__List_ANY(space, w_list, w_index):
    idx = space.int_w(w_index)
    if idx < 0:
        idx += w_list.ob_size
    if idx < 0 or idx >= w_list.ob_size:
        raise OperationError(space.w_IndexError,
                             space.wrap("list index out of range"))
    w_item = w_list.ob_item[idx]
    return w_item

def getitem__List_Slice(space, w_list, w_slice):
    length = w_list.ob_size
    start, stop, step, slicelength = slicetype.indices4(space, w_slice, length)
    assert slicelength >= 0
    w_res = W_ListObject(space, [])
    _list_resize(w_res, slicelength)
    items = w_list.ob_item
    subitems = w_res.ob_item
    for i in range(slicelength):
        subitems[i] = items[start]
        start += step
    w_res.ob_size = slicelength
    return w_res

def contains__List_ANY(space, w_list, w_obj):
    # needs to be safe against eq_w() mutating the w_list behind our back
    i = 0
    while i < w_list.ob_size:
        if space.eq_w(w_list.ob_item[i], w_obj):
            return space.w_True
        i += 1
    return space.w_False

def iter__List(space, w_list):
    from pypy.objspace.std import iterobject
    return iterobject.W_SeqIterObject(space, w_list)

def add__List_List(space, w_list1, w_list2):
    w_res = W_ListObject(space, [])
    newlen = w_list1.ob_size + w_list2.ob_size
    _list_resize(w_res, newlen)
    p = 0
    items = w_res.ob_item
    src = w_list1.ob_item
    for i in range(w_list1.ob_size):
        items[p] = src[i]
        p += 1
    src = w_list2.ob_item
    for i in range(w_list2.ob_size):
        items[p] = src[i]
        p += 1
    w_res.ob_size = p
    return w_res

def inplace_add__List_ANY(space, w_list1, w_iterable2):
    list_extend__List_ANY(space, w_list1, w_iterable2)
    return w_list1

def mul_list_times(space, w_list, w_times):
    try:
        times = space.int_w(w_times)
    except OperationError, e:
        if e.match(space, space.w_TypeError):
            raise FailedToImplement
        raise
    w_res = W_ListObject(space, [])
    size = w_list.ob_size
    newlen = size * times  # XXX check overflow
    _list_resize(w_res, newlen)
    src = w_list.ob_item
    items = w_res.ob_item
    p = 0
    for _ in range(times):
        for i in range(size):
            items[p] = src[i]
            p += 1
    w_res.ob_size = p
    return w_res

def mul__List_ANY(space, w_list, w_times):
    return mul_list_times(space, w_list, w_times)

def mul__ANY_List(space, w_times, w_list):
    return mul_list_times(space, w_list, w_times)

def inplace_mul__List_ANY(space, w_list, w_times):
    try:
        times = space.int_w(w_times)
    except OperationError, e:
        if e.match(space, space.w_TypeError):
            raise FailedToImplement
        raise
    if times <= 0:
        w_list.clear()
        return w_list
    size = w_list.ob_size
    newlen = size * times  # XXX check overflow
    _list_resize(w_list, newlen)
    items = w_list.ob_item
    p = size
    for _ in range(1, times):
        for i in range(size):
            items[p] = items[i]
            p += 1
    w_list.ob_size = newlen
    return w_list

def eq__List_List(space, w_list1, w_list2):
    # needs to be safe against eq_w() mutating the w_lists behind our back
    if w_list1.ob_size != w_list2.ob_size:
        return space.w_False
    i = 0
    while i < w_list1.ob_size and i < w_list2.ob_size:
        if not space.eq_w(w_list1.ob_item[i], w_list2.ob_item[i]):
            return space.w_False
        i += 1
    return space.newbool(w_list1.ob_size == w_list2.ob_size)

def _min(a, b):
    if a < b:
        return a
    return b

def lt__List_List(space, w_list1, w_list2):
    # needs to be safe against eq_w() mutating the w_lists behind our back
    # Search for the first index where items are different
    i = 0
    while i < w_list1.ob_size and i < w_list2.ob_size:
        w_item1 = w_list1.ob_item[i]
        w_item2 = w_list2.ob_item[i]
        if not space.eq_w(w_item1, w_item2):
            return space.lt(w_item1, w_item2)
        i += 1
    # No more items to compare -- compare sizes
    return space.newbool(w_list1.ob_size < w_list2.ob_size)

def gt__List_List(space, w_list1, w_list2):
    # needs to be safe against eq_w() mutating the w_lists behind our back
    # Search for the first index where items are different
    i = 0
    while i < w_list1.ob_size and i < w_list2.ob_size:
        w_item1 = w_list1.ob_item[i]
        w_item2 = w_list2.ob_item[i]
        if not space.eq_w(w_item1, w_item2):
            return space.gt(w_item1, w_item2)
        i += 1
    # No more items to compare -- compare sizes
    return space.newbool(w_list1.ob_size > w_list2.ob_size)

# upto here, lists are nearly identical to tuples, despite the
# fact that we now support over-allocation!

def delitem__List_ANY(space, w_list, w_idx):
    i = space.int_w(w_idx)
    if i < 0:
        i += w_list.ob_size
    if i < 0 or i >= w_list.ob_size:
        raise OperationError(space.w_IndexError,
                             space.wrap("list deletion index out of range"))
    _del_slice(w_list, i, i+1)
    return space.w_None

def delitem__List_Slice(space, w_list, w_slice):
    start, stop, step, slicelength = slicetype.indices4(space, w_slice, w_list.ob_size)
    if step == 1:
        return _setitem_slice_helper(space, w_list, w_slice, [], 0)

    # The current code starts from the top, to simplify
    # coding.  A later optimization could be to start from
    # the bottom, which would reduce the list motion.
    # A further later optimization would be to special-case
    # a step of -1, because this version will perform a LOT
    # of extra motion for this case.  Anybody with a real-life
    # use-case for this is welcome to write the special case.
    r = range(start, stop, step)
    if step > 0:
        r.reverse()
    for i in r:
        _del_slice(w_list, i, i+1)
    return space.w_None

def setitem__List_ANY_ANY(space, w_list, w_index, w_any):
    idx = space.int_w(w_index)
    if idx < 0:
        idx += w_list.ob_size
    if idx < 0 or idx >= w_list.ob_size:
        raise OperationError(space.w_IndexError,
                             space.wrap("list index out of range"))
    w_list.ob_item[idx] = w_any
    return space.w_None

def setitem__List_Slice_List(space, w_list, w_slice, w_list2):
    return _setitem_slice_helper(space, w_list, w_slice, w_list2.ob_item, w_list2.ob_size)

def setitem__List_Slice_Tuple(space, w_list, w_slice, w_tuple):
    t = w_tuple.wrappeditems
    return _setitem_slice_helper(space, w_list, w_slice, t, len(t))

def setitem__List_Slice_ANY(space, w_list, w_slice, w_iterable):
##    if isinstance(w_iterable, W_ListObject):
##        return _setitem_slice_helper(space, w_list, w_slice,
##                                     w_iterable.ob_item, w_iterable.ob_size)
##    if isinstance(w_iterable, W_TupleObject):
##        t = w_iterable.wrappeditems
##    else:
    t = space.unpackiterable(w_iterable)
    return _setitem_slice_helper(space, w_list, w_slice, t, len(t))

def _setitem_slice_helper(space, w_list, w_slice, sequence2, len2):
    start, stop, step, slicelength = slicetype.indices4(space, w_slice, w_list.ob_size)
    assert slicelength >= 0

    if step == 1:  # Support list resizing for non-extended slices
        oldsize = w_list.ob_size
        delta = len2 - slicelength
        newsize = oldsize + delta
        if delta >= 0:
            _list_resize(w_list, newsize)
            w_list.ob_size = newsize
            items = w_list.ob_item
            for i in range(newsize-1, start+len2-1, -1):
                items[i] = items[i-delta]
        else:
            # shrinking requires the careful memory management of _del_slice()
            _del_slice(w_list, start, start-delta)
    elif len2 != slicelength:  # No resize for extended slices
        raise OperationError(space.w_ValueError, space.wrap("attempt to "
              "assign sequence of size %d to extended slice of size %d" %
              (len2,slicelength)))

    r = range(len2)
    items = w_list.ob_item
    if sequence2 is items:
        if step > 0:
            # Always copy starting from the right to avoid
            # having to make a shallow copy in the case where
            # the source and destination lists are the same list.
            r.reverse()
        else:
            # Make a shallow copy to more easily handle the reversal case
            sequence2 = list(sequence2)
    for i in r:
        items[start+i*step] = sequence2[i]
    return space.w_None

app = gateway.applevel("""
    def listrepr(currently_in_repr, l):
        'The app-level part of repr().'
        list_id = id(l)
        if list_id in currently_in_repr:
            return '[...]'
        currently_in_repr[list_id] = 1
        try:
            return "[" + ", ".join([repr(x) for x in l]) + ']'
        finally:
            try:
                del currently_in_repr[list_id]
            except:
                pass
""", filename=__file__) 

listrepr = app.interphook("listrepr")

def repr__List(space, w_list):
    if w_list.ob_size == 0:
        return space.wrap('[]')
    w_currently_in_repr = space.getexecutioncontext()._py_repr
    return listrepr(space, w_currently_in_repr, w_list)

def hash__List(space,w_list):
    raise OperationError(space.w_TypeError,space.wrap("list objects are unhashable"))

# adapted C code
def _roundupsize(n):
    nbits = r_uint(0)
    n2 = n >> 5

##    /* Round up:
##     * If n <       256, to a multiple of        8.
##     * If n <      2048, to a multiple of       64.
##     * If n <     16384, to a multiple of      512.
##     * If n <    131072, to a multiple of     4096.
##     * If n <   1048576, to a multiple of    32768.
##     * If n <   8388608, to a multiple of   262144.
##     * If n <  67108864, to a multiple of  2097152.
##     * If n < 536870912, to a multiple of 16777216.
##     * ...
##     * If n < 2**(5+3*i), to a multiple of 2**(3*i).
##     *
##     * This over-allocates proportional to the list size, making room
##     * for additional growth.  The over-allocation is mild, but is
##     * enough to give linear-time amortized behavior over a long
##     * sequence of appends() in the presence of a poorly-performing
##     * system realloc() (which is a reality, e.g., across all flavors
##     * of Windows, with Win9x behavior being particularly bad -- and
##     * we've still got address space fragmentation problems on Win9x
##     * even with this scheme, although it requires much longer lists to
##     * provoke them than it used to).
##     */
    while 1:
        n2 >>= 3
        nbits += 3
        if not n2 :
            break
    return ((n >> nbits) + 1) << nbits

# before we have real arrays,
# we use lists, allocated to fixed size.
# XXX memory overflow is ignored here.
# See listobject.c for reference.

for_later = """
#define NRESIZE(var, type, nitems)              \
do {                                \
    size_t _new_size = _roundupsize(nitems);         \
    if (_new_size <= ((~(size_t)0) / sizeof(type)))     \
        PyMem_RESIZE(var, type, _new_size);     \
    else                            \
        var = NULL;                 \
} while (0)
"""

def _list_resize(w_list, newlen):
    if newlen > len(w_list.ob_item):
        true_size = _roundupsize(newlen)
        old_items = w_list.ob_item
        w_list.ob_item = items = [None] * true_size
        for p in range(len(old_items)):
            items[p] = old_items[p]

def _ins1(w_list, where, w_any):
    _list_resize(w_list, w_list.ob_size+1)
    size = w_list.ob_size
    items = w_list.ob_item
    if where < 0:
        where += size
    if where < 0:
        where = 0
    if (where > size):
        where = size
    for i in range(size, where, -1):
        items[i] = items[i-1]
    items[where] = w_any
    w_list.ob_size += 1

def list_insert__List_ANY_ANY(space, w_list, w_where, w_any):
    _ins1(w_list, space.int_w(w_where), w_any)
    return space.w_None

def list_append__List_ANY(space, w_list, w_any):
    _ins1(w_list, w_list.ob_size, w_any)
    return space.w_None

def list_extend__List_ANY(space, w_list, w_any):
    lis = space.unpackiterable(w_any)
    newlen = w_list.ob_size + len(lis)
    _list_resize(w_list, newlen)
    d = w_list.ob_size
    items = w_list.ob_item
    for i in range(len(lis)):
        items[d+i] = lis[i]
    w_list.ob_size = newlen
    return space.w_None

def _del_slice(w_list, ilow, ihigh):
    """ similar to the deletion part of list_ass_slice in CPython """
    if ilow < 0:
        ilow = 0
    elif ilow > w_list.ob_size:
        ilow = w_list.ob_size
    if ihigh < ilow:
        ihigh = ilow
    elif ihigh > w_list.ob_size:
        ihigh = w_list.ob_size
    items = w_list.ob_item
    d = ihigh-ilow
    # keep a reference to the objects to be removed,
    # preventing side effects during destruction
    recycle = [items[i] for i in range(ilow, ihigh)]
    for i in range(ilow, w_list.ob_size - d):
        items[i] = items[i+d]
        items[i+d] = None
    # make sure entries after ob_size-d are None, to avoid keeping references
    # (the above loop already set to None all items[ilow+d:old_style])
    w_list.ob_size -= d
    for i in range(w_list.ob_size, ilow + d):
        items[i] = None
    # now we can destruct recycle safely, regardless of
    # side-effects to the list
    del recycle[:]

# note that the default value will come back wrapped!!!
def list_pop__List_ANY(space, w_list, w_idx=-1):
    if w_list.ob_size == 0:
        raise OperationError(space.w_IndexError,
                             space.wrap("pop from empty list"))
    i = space.int_w(w_idx)
    if i < 0:
        i += w_list.ob_size
    if i < 0 or i >= w_list.ob_size:
        raise OperationError(space.w_IndexError,
                             space.wrap("pop index out of range"))
    w_res = w_list.ob_item[i]
    _del_slice(w_list, i, i+1)
    return w_res

def list_remove__List_ANY(space, w_list, w_any):
    # needs to be safe against eq_w() mutating the w_list behind our back
    i = 0
    while i < w_list.ob_size:
        if space.eq_w(w_list.ob_item[i], w_any):
            _del_slice(w_list, i, i+1)
            return space.w_None
        i += 1
    raise OperationError(space.w_ValueError,
                         space.wrap("list.remove(x): x not in list"))

def list_index__List_ANY_ANY_ANY(space, w_list, w_any, w_start, w_stop):
    # needs to be safe against eq_w() mutating the w_list behind our back
    size = w_list.ob_size
    w_start = slicetype.adapt_bound(space, w_start, space.wrap(size))
    w_stop = slicetype.adapt_bound(space, w_stop, space.wrap(size))
    i = space.int_w(w_start)
    stop = space.int_w(w_stop)
    while i < stop and i < w_list.ob_size:
        if space.eq_w(w_list.ob_item[i], w_any):
            return space.wrap(i)
        i += 1
    raise OperationError(space.w_ValueError,
                         space.wrap("list.index(x): x not in list"))

def list_count__List_ANY(space, w_list, w_any):
    # needs to be safe against eq_w() mutating the w_list behind our back
    count = 0
    i = 0
    while i < w_list.ob_size:
        if space.eq_w(w_list.ob_item[i], w_any):
            count += 1
        i += 1
    return space.wrap(count)

# Reverse a slice of a list in place, from lo up to (exclusive) hi.
# (also used in sort, later)

def _reverse_slice(lis, lo, hi):
    hi -= 1
    while lo < hi:
        t = lis[lo]
        lis[lo] = lis[hi]
        lis[hi] = t
        lo += 1
        hi -= 1

def list_reverse__List(space, w_list):
    if w_list.ob_size > 1:
        _reverse_slice(w_list.ob_item, 0, w_list.ob_size)
    return space.w_None

# ____________________________________________________________
# Sorting

class KeyContainer(baseobjspace.W_Root):
    def __init__(self, w_key, w_item):
        self.w_key = w_key
        self.w_item = w_item

class SimpleSort(TimSort):
    def lt(self, a, b):
        space = self.space
        return space.is_true(space.lt(a, b))

class CustomCompareSort(TimSort):
    def lt(self, a, b):
        space = self.space
        w_cmp = self.w_cmp
        w_result = space.call_function(w_cmp, a, b)
        try:
            result = space.int_w(w_result)
        except OperationError, e:
            if e.match(space, space.w_TypeError):
                raise OperationError(space.w_TypeError,
                    space.wrap("comparison function must return int"))
            raise
        return result < 0

class CustomKeySort(TimSort):
    def lt(self, a, b):
        assert isinstance(a, KeyContainer)
        assert isinstance(b, KeyContainer)
        space = self.space
        return space.is_true(space.lt(a.w_key, b.w_key))

class CustomKeyCompareSort(CustomCompareSort):
    def lt(self, a, b):
        assert isinstance(a, KeyContainer)
        assert isinstance(b, KeyContainer)
        return CustomCompareSort.lt(self, a.w_key, b.w_key)

SortClass = {
    (False, False): SimpleSort,
    (True,  False): CustomCompareSort,
    (False, True) : CustomKeySort,
    (True,  True) : CustomKeyCompareSort,
    }

def list_sort__List_ANY_ANY_ANY(space, w_list, w_cmp, w_keyfunc, w_reverse):
    has_cmp = not space.is_w(w_cmp, space.w_None)
    has_key = not space.is_w(w_keyfunc, space.w_None)
    has_reverse = space.is_true(w_reverse)

    # create and setup a TimSort instance
    sorterclass = SortClass[has_cmp, has_key]
    sorter = sorterclass(w_list.ob_item, w_list.ob_size)
    sorter.space = space
    sorter.w_cmp = w_cmp

    try:
        # The list is temporarily made empty, so that mutations performed
        # by comparison functions can't affect the slice of memory we're
        # sorting (allowing mutations during sorting is an IndexError or
        # core-dump factory, since ob_item may change).
        w_list.clear()

        # wrap each item in a KeyContainer if needed
        if has_key:
            for i in range(sorter.listlength):
                w_item = sorter.list[i]
                w_key = space.call_function(w_keyfunc, w_item)
                sorter.list[i] = KeyContainer(w_key, w_item)

        # Reverse sort stability achieved by initially reversing the list,
        # applying a stable forward sort, then reversing the final result.
        if has_reverse:
            _reverse_slice(sorter.list, 0, sorter.listlength)

        # perform the sort
        sorter.sort()

        # check if the user mucked with the list during the sort
        if w_list.ob_item:
            raise OperationError(space.w_ValueError,
                                 space.wrap("list modified during sort"))

    finally:
        # unwrap each item if needed
        if has_key:
            for i in range(sorter.listlength):
                w_obj = sorter.list[i]
                if isinstance(w_obj, KeyContainer):
                    sorter.list[i] = w_obj.w_item

        if has_reverse:
            _reverse_slice(sorter.list, 0, sorter.listlength)

        # put the items back into the list
        w_list.ob_item = sorter.list
        w_list.ob_size = sorter.listlength

    return space.w_None


from pypy.objspace.std import listtype
register_all(vars(), listtype)

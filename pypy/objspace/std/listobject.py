from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.multimethod import FailedToImplement
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.objspace.std.inttype import wrapint
from pypy.objspace.std.listtype import get_list_index
from pypy.objspace.std.sliceobject import W_SliceObject, normalize_simple_slice

from pypy.objspace.std import slicetype
from pypy.interpreter import gateway, baseobjspace
from pypy.rlib.listsort import make_timsort_class
from pypy.interpreter.argument import Signature

class W_AbstractListObject(W_Object):
    pass

class W_ListObject(W_AbstractListObject):
    from pypy.objspace.std.listtype import list_typedef as typedef

    def __init__(w_self, wrappeditems):
        w_self.wrappeditems = wrappeditems

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%s)" % (w_self.__class__.__name__, w_self.wrappeditems)

    def unwrap(w_list, space):
        items = [space.unwrap(w_item) for w_item in w_list.wrappeditems]# XXX generic mixed types unwrap
        return list(items)

    def append(w_list, w_item):
        w_list.wrappeditems.append(w_item)

registerimplementation(W_ListObject)


init_signature = Signature(['sequence'], None, None)
init_defaults = [None]

def init__List(space, w_list, __args__):
    from pypy.objspace.std.tupleobject import W_TupleObject
    # this is on the silly side
    w_iterable, = __args__.parse_obj(
            None, 'list', init_signature, init_defaults)
    items_w = w_list.wrappeditems
    del items_w[:]
    if w_iterable is not None:
        # unfortunately this is duplicating space.unpackiterable to avoid
        # assigning a new RPython list to 'wrappeditems', which defeats the
        # W_FastListIterObject optimization.
        if isinstance(w_iterable, W_ListObject):
            items_w.extend(w_iterable.wrappeditems)
        elif isinstance(w_iterable, W_TupleObject):
            items_w.extend(w_iterable.wrappeditems)
        else:
            _init_from_iterable(space, items_w, w_iterable)

def _init_from_iterable(space, items_w, w_iterable):
    # in its own function to make the JIT look into init__List
    # xxx special hack for speed
    from pypy.interpreter.generator import GeneratorIterator
    if isinstance(w_iterable, GeneratorIterator):
        w_iterable.unpack_into(items_w)
        return
    # /xxx
    w_iterator = space.iter(w_iterable)
    while True:
        try:
            w_item = space.next(w_iterator)
        except OperationError, e:
            if not e.match(space, space.w_StopIteration):
                raise
            break  # done
        items_w.append(w_item)

def len__List(space, w_list):
    result = len(w_list.wrappeditems)
    return wrapint(space, result)

def getitem__List_ANY(space, w_list, w_index):
    try:
        return w_list.wrappeditems[get_list_index(space, w_index)]
    except IndexError:
        raise OperationError(space.w_IndexError,
                             space.wrap("list index out of range"))

def getitem__List_Slice(space, w_list, w_slice):
    # XXX consider to extend rlist's functionality?
    length = len(w_list.wrappeditems)
    start, stop, step, slicelength = w_slice.indices4(space, length)
    assert slicelength >= 0
    if step == 1 and 0 <= start <= stop:
        return W_ListObject(w_list.wrappeditems[start:stop])
    w_res = W_ListObject([None] * slicelength)
    items_w = w_list.wrappeditems
    subitems_w = w_res.wrappeditems
    for i in range(slicelength):
        subitems_w[i] = items_w[start]
        start += step
    return w_res

def getslice__List_ANY_ANY(space, w_list, w_start, w_stop):
    length = len(w_list.wrappeditems)
    start, stop = normalize_simple_slice(space, length, w_start, w_stop)
    return W_ListObject(w_list.wrappeditems[start:stop])

def setslice__List_ANY_ANY_ANY(space, w_list, w_start, w_stop, w_sequence):
    length = len(w_list.wrappeditems)
    start, stop = normalize_simple_slice(space, length, w_start, w_stop)

    sequence2 = space.listview(w_sequence)
    items = w_list.wrappeditems
    _setitem_slice_helper(space, items, start, 1, stop-start, sequence2,
                          empty_elem=None)

def delslice__List_ANY_ANY(space, w_list, w_start, w_stop):
    length = len(w_list.wrappeditems)
    start, stop = normalize_simple_slice(space, length, w_start, w_stop)
    _delitem_slice_helper(space, w_list.wrappeditems, start, 1, stop-start)

def contains__List_ANY(space, w_list, w_obj):
    # needs to be safe against eq_w() mutating the w_list behind our back
    i = 0
    items_w = w_list.wrappeditems
    while i < len(items_w): # intentionally always calling len!
        if space.eq_w(items_w[i], w_obj):
            return space.w_True
        i += 1
    return space.w_False

def iter__List(space, w_list):
    from pypy.objspace.std import iterobject
    return iterobject.W_FastListIterObject(w_list, w_list.wrappeditems)

def add__List_List(space, w_list1, w_list2):
    return W_ListObject(w_list1.wrappeditems + w_list2.wrappeditems)


def inplace_add__List_ANY(space, w_list1, w_iterable2):
    try:
        list_extend__List_ANY(space, w_list1, w_iterable2)
    except OperationError, e:
        if e.match(space, space.w_TypeError):
            raise FailedToImplement
        raise
    return w_list1

def inplace_add__List_List(space, w_list1, w_list2):
    list_extend__List_List(space, w_list1, w_list2)
    return w_list1

def mul_list_times(space, w_list, w_times):
    try:
        times = space.getindex_w(w_times, space.w_OverflowError)
    except OperationError, e:
        if e.match(space, space.w_TypeError):
            raise FailedToImplement
        raise
    return W_ListObject(w_list.wrappeditems * times)

def mul__List_ANY(space, w_list, w_times):
    return mul_list_times(space, w_list, w_times)

def mul__ANY_List(space, w_times, w_list):
    return mul_list_times(space, w_list, w_times)

def inplace_mul__List_ANY(space, w_list, w_times):
    try:
        times = space.getindex_w(w_times, space.w_OverflowError)
    except OperationError, e:
        if e.match(space, space.w_TypeError):
            raise FailedToImplement
        raise
    w_list.wrappeditems *= times
    return w_list

def eq__List_List(space, w_list1, w_list2):
    # needs to be safe against eq_w() mutating the w_lists behind our back
    items1_w = w_list1.wrappeditems
    items2_w = w_list2.wrappeditems
    return equal_wrappeditems(space, items1_w, items2_w)

def equal_wrappeditems(space, items1_w, items2_w):
    if len(items1_w) != len(items2_w):
        return space.w_False
    i = 0
    while i < len(items1_w) and i < len(items2_w):
        if not space.eq_w(items1_w[i], items2_w[i]):
            return space.w_False
        i += 1
    return space.w_True

def lessthan_unwrappeditems(space, items1_w, items2_w):
    # needs to be safe against eq_w() mutating the w_lists behind our back
    # Search for the first index where items are different
    i = 0
    while i < len(items1_w) and i < len(items2_w):
        w_item1 = items1_w[i]
        w_item2 = items2_w[i]
        if not space.eq_w(w_item1, w_item2):
            return space.lt(w_item1, w_item2)
        i += 1
    # No more items to compare -- compare sizes
    return space.newbool(len(items1_w) < len(items2_w))

def greaterthan_unwrappeditems(space, items1_w, items2_w):
    # needs to be safe against eq_w() mutating the w_lists behind our back
    # Search for the first index where items are different
    i = 0
    while i < len(items1_w) and i < len(items2_w):
        w_item1 = items1_w[i]
        w_item2 = items2_w[i]
        if not space.eq_w(w_item1, w_item2):
            return space.gt(w_item1, w_item2)
        i += 1
    # No more items to compare -- compare sizes
    return space.newbool(len(items1_w) > len(items2_w))

def lt__List_List(space, w_list1, w_list2):
    return lessthan_unwrappeditems(space, w_list1.wrappeditems,
        w_list2.wrappeditems)

def gt__List_List(space, w_list1, w_list2):
    return greaterthan_unwrappeditems(space, w_list1.wrappeditems,
        w_list2.wrappeditems)

def delitem__List_ANY(space, w_list, w_idx):
    idx = get_list_index(space, w_idx)
    try:
        del w_list.wrappeditems[idx]
    except IndexError:
        raise OperationError(space.w_IndexError,
                             space.wrap("list deletion index out of range"))
    return space.w_None


def delitem__List_Slice(space, w_list, w_slice):
    start, stop, step, slicelength = w_slice.indices4(space,
                                                      len(w_list.wrappeditems))
    _delitem_slice_helper(space, w_list.wrappeditems, start, step, slicelength)

def _delitem_slice_helper(space, items, start, step, slicelength):
    if slicelength==0:
        return

    if step < 0:
        start = start + step * (slicelength-1)
        step = -step

    if step == 1:
        assert start >= 0
        assert slicelength >= 0
        del items[start:start+slicelength]
    else:
        n = len(items)
        i = start

        for discard in range(1, slicelength):
            j = i+1
            i += step
            while j < i:
                items[j-discard] = items[j]
                j += 1

        j = i+1
        while j < n:
            items[j-slicelength] = items[j]
            j += 1
        start = n - slicelength
        assert start >= 0 # annotator hint
        del items[start:]

def setitem__List_ANY_ANY(space, w_list, w_index, w_any):
    idx = get_list_index(space, w_index)
    try:
        w_list.wrappeditems[idx] = w_any
    except IndexError:
        raise OperationError(space.w_IndexError,
                             space.wrap("list index out of range"))
    return space.w_None

def setitem__List_Slice_ANY(space, w_list, w_slice, w_iterable):
    oldsize = len(w_list.wrappeditems)
    start, stop, step, slicelength = w_slice.indices4(space, oldsize)

    sequence2 = space.listview(w_iterable)
    items = w_list.wrappeditems
    _setitem_slice_helper(space, items, start, step, slicelength, sequence2,
                          empty_elem=None)

def _setitem_slice_helper(space, items, start, step, slicelength, sequence2,
                          empty_elem):
    assert slicelength >= 0
    oldsize = len(items)
    len2 = len(sequence2)
    if step == 1:  # Support list resizing for non-extended slices
        delta = slicelength - len2
        if delta < 0:
            delta = -delta
            newsize = oldsize + delta
            # XXX support this in rlist!
            items += [empty_elem] * delta
            lim = start+len2
            i = newsize - 1
            while i >= lim:
                items[i] = items[i-delta]
                i -= 1
        elif start >= 0:
            del items[start:start+delta]
        else:
            assert delta==0   # start<0 is only possible with slicelength==0
    elif len2 != slicelength:  # No resize for extended slices
        raise operationerrfmt(space.w_ValueError, "attempt to "
              "assign sequence of size %d to extended slice of size %d",
              len2, slicelength)

    if sequence2 is items:
        if step > 0:
            # Always copy starting from the right to avoid
            # having to make a shallow copy in the case where
            # the source and destination lists are the same list.
            i = len2 - 1
            start += i*step
            while i >= 0:
                items[start] = sequence2[i]
                start -= step
                i -= 1
            return
        else:
            # Make a shallow copy to more easily handle the reversal case
            sequence2 = list(sequence2)
    for i in range(len2):
        items[start] = sequence2[i]
        start += step

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
    if len(w_list.wrappeditems) == 0:
        return space.wrap('[]')
    ec = space.getexecutioncontext()
    w_currently_in_repr = ec._py_repr
    if w_currently_in_repr is None:
        w_currently_in_repr = ec._py_repr = space.newdict()
    return listrepr(space, w_currently_in_repr, w_list)

def list_insert__List_ANY_ANY(space, w_list, w_where, w_any):
    where = space.int_w(w_where)
    length = len(w_list.wrappeditems)
    index = get_positive_index(where, length)
    w_list.wrappeditems.insert(index, w_any)
    return space.w_None

def get_positive_index(where, length):
    if where < 0:
        where += length
        if where < 0:
            where = 0
    elif where > length:
        where = length
    return where

def list_append__List_ANY(space, w_list, w_any):
    w_list.wrappeditems.append(w_any)
    return space.w_None

def list_extend__List_List(space, w_list, w_other):
    w_list.wrappeditems += w_other.wrappeditems
    return space.w_None

def list_extend__List_ANY(space, w_list, w_any):
    w_list.wrappeditems += space.listview(w_any)
    return space.w_None

# note that the default value will come back wrapped!!!
def list_pop__List_ANY(space, w_list, w_idx=-1):
    items = w_list.wrappeditems
    if len(items)== 0:
        raise OperationError(space.w_IndexError,
                             space.wrap("pop from empty list"))
    if space.isinstance_w(w_idx, space.w_float):
        raise OperationError(space.w_TypeError,
            space.wrap("integer argument expected, got float")
        )
    idx = space.int_w(space.int(w_idx))
    try:
        return items.pop(idx)
    except IndexError:
        raise OperationError(space.w_IndexError,
                             space.wrap("pop index out of range"))

def list_remove__List_ANY(space, w_list, w_any):
    # needs to be safe against eq_w() mutating the w_list behind our back
    items = w_list.wrappeditems
    i = 0
    while i < len(items):
        if space.eq_w(items[i], w_any):
            if i < len(items): # if this is wrong the list was changed
                del items[i]
            return space.w_None
        i += 1
    raise OperationError(space.w_ValueError,
                         space.wrap("list.remove(x): x not in list"))

def list_index__List_ANY_ANY_ANY(space, w_list, w_any, w_start, w_stop):
    # needs to be safe against eq_w() mutating the w_list behind our back
    items = w_list.wrappeditems
    size = len(items)
    i, stop = slicetype.unwrap_start_stop(
            space, size, w_start, w_stop, True)
    while i < stop and i < len(items):
        if space.eq_w(items[i], w_any):
            return space.wrap(i)
        i += 1
    raise OperationError(space.w_ValueError,
                         space.wrap("list.index(x): x not in list"))

def list_count__List_ANY(space, w_list, w_any):
    # needs to be safe against eq_w() mutating the w_list behind our back
    count = 0
    i = 0
    items = w_list.wrappeditems
    while i < len(items):
        if space.eq_w(items[i], w_any):
            count += 1
        i += 1
    return space.wrap(count)

def list_reverse__List(space, w_list):
    w_list.wrappeditems.reverse()
    return space.w_None

# ____________________________________________________________
# Sorting

# Reverse a slice of a list in place, from lo up to (exclusive) hi.
# (used in sort)

class KeyContainer(baseobjspace.W_Root):
    def __init__(self, w_key, w_item):
        self.w_key = w_key
        self.w_item = w_item

TimSort = make_timsort_class()
# NOTE: all the subclasses of TimSort should inherit from a common subclass,
#       so make sure that only SimpleSort inherits directly from TimSort.
#       This is necessary to hide the parent method TimSort.lt() from the
#       annotator.
class SimpleSort(TimSort):
    def lt(self, a, b):
        space = self.space
        return space.is_true(space.lt(a, b))

class CustomCompareSort(SimpleSort):
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

class CustomKeySort(SimpleSort):
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

def list_sort__List_ANY_ANY_ANY(space, w_list, w_cmp, w_keyfunc, w_reverse):
    has_cmp = not space.is_w(w_cmp, space.w_None)
    has_key = not space.is_w(w_keyfunc, space.w_None)
    has_reverse = space.is_true(w_reverse)

    # create and setup a TimSort instance
    if has_cmp:
        if has_key:
            sorterclass = CustomKeyCompareSort
        else:
            sorterclass = CustomCompareSort
    else:
        if has_key:
            sorterclass = CustomKeySort
        else:
            sorterclass = SimpleSort
    items = w_list.wrappeditems
    sorter = sorterclass(items, len(items))
    sorter.space = space
    sorter.w_cmp = w_cmp

    try:
        # The list is temporarily made empty, so that mutations performed
        # by comparison functions can't affect the slice of memory we're
        # sorting (allowing mutations during sorting is an IndexError or
        # core-dump factory, since wrappeditems may change).
        w_list.wrappeditems = []

        # wrap each item in a KeyContainer if needed
        if has_key:
            for i in range(sorter.listlength):
                w_item = sorter.list[i]
                w_key = space.call_function(w_keyfunc, w_item)
                sorter.list[i] = KeyContainer(w_key, w_item)

        # Reverse sort stability achieved by initially reversing the list,
        # applying a stable forward sort, then reversing the final result.
        if has_reverse:
            sorter.list.reverse()

        # perform the sort
        sorter.sort()

        # reverse again
        if has_reverse:
            sorter.list.reverse()

    finally:
        # unwrap each item if needed
        if has_key:
            for i in range(sorter.listlength):
                w_obj = sorter.list[i]
                if isinstance(w_obj, KeyContainer):
                    sorter.list[i] = w_obj.w_item

        # check if the user mucked with the list during the sort
        mucked = len(w_list.wrappeditems) > 0

        # put the items back into the list
        w_list.wrappeditems = sorter.list

    if mucked:
        raise OperationError(space.w_ValueError,
                             space.wrap("list modified during sort"))

    return space.w_None


from pypy.objspace.std import listtype
register_all(vars(), listtype)

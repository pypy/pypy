"""
The class pypystm.stmset, giving a part of the regular 'set' interface
"""

from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app

from rpython.rlib import rstm, jit, rerased
from rpython.rlib.rgc import ll_arraycopy
from rpython.rlib.objectmodel import specialize
from rpython.rtyper.lltypesystem import lltype, llmemory

ARRAY = lltype.GcArray(llmemory.GCREF)
PARRAY = lltype.Ptr(ARRAY)

erase, unerase = rerased.new_erasing_pair("stmdictitem")


# XXX: should have identity-dict strategy
def really_find_equal_item(space, h, w_key):
    hkey = space.hash_w(w_key)
    entry = h.lookup(hkey)
    array = lltype.cast_opaque_ptr(PARRAY, entry.object)
    if not array:
        return (entry, array, -1)
    if space.type(w_key).compares_by_identity():
        # fastpath
        return (entry, array, _find_equal_item(space, array, w_key))
    # slowpath
    return _really_find_equal_item_loop(space, h, w_key, entry, array, hkey)

@jit.dont_look_inside
def _really_find_equal_item_loop(space, h, w_key, entry, array, hkey):
    assert not space.type(w_key).compares_by_identity() # assume it stays that way
    while True:
        assert array
        i = _find_equal_item(space, array, w_key)
        # custom __eq__ may have been called in _find_equal_item()
        #
        # Only if entry.object changed during the call to _find_equal_item()
        # we have to re-lookup the entry. This is ok since entry.object=array!=NULL
        # when we enter here and therefore, entry can only be thrown out of
        # the hashtable if it gets NULLed somehow, thus, changing entry.object.
        array2 = lltype.cast_opaque_ptr(PARRAY, entry.object)
        if array != array2:
            # re-get entry (and array)
            entry = h.lookup(hkey)
            array = lltype.cast_opaque_ptr(PARRAY, entry.object)
            if not array:
                return (entry, array, -1)
            continue

        return (entry, array, i)


def _find_equal_item(space, array, w_key):
    # result by this function is based on 'array'. If the entry
    # changes, the result is stale.
    w_item = unerase(array[0])
    if space.eq_w(w_key, w_item):
        return 0
    if len(array) > 1:
        return _run_next_iterations(space, array, w_key)
    return -1


@jit.dont_look_inside
def _run_next_iterations(space, array, w_key):
    i = 1
    limit = len(array)
    while True:
        w_item = unerase(array[i])
        if space.eq_w(w_key, w_item):
            return i
        i += 1
        if i >= limit:
            return -1


class W_STMSet(W_Root):

    def __init__(self):
        self.h = rstm.create_hashtable()

    def contains_w(self, space, w_key):
        entry, array, i = really_find_equal_item(space, self.h, w_key)
        if array and i >= 0:
            return space.w_True
        return space.w_False

    def add_w(self, space, w_key):
        entry, array, i = really_find_equal_item(space, self.h, w_key)
        if array:
            if i >= 0:
                return      # already there
            L = len(array)
            narray = lltype.malloc(ARRAY, L + 1)
            ll_arraycopy(array, narray, 0, 0, L)
        else:
            narray = lltype.malloc(ARRAY, 1)
            L = 0

        narray[L] = erase(w_key)
        self.h.writeobj(entry, lltype.cast_opaque_ptr(llmemory.GCREF, narray))

    def try_remove(self, space, w_key):
        entry, array, i = really_find_equal_item(space, self.h, w_key)
        if not array or i < 0:
            return False
        # found
        L = len(array) - 1
        if L == 0:
            narray = lltype.nullptr(ARRAY)
        else:
            narray = lltype.malloc(ARRAY, L)
            ll_arraycopy(array, narray, 0, 0, i)
            ll_arraycopy(array, narray, i + 1, i, L - i)
        self.h.writeobj(entry, lltype.cast_opaque_ptr(llmemory.GCREF, narray))
        return True

    def remove_w(self, space, w_key):
        if not self.try_remove(space, w_key):
            space.raise_key_error(w_key)

    def discard_w(self, space, w_key):
        self.try_remove(space, w_key)

    def get_length(self):
        array, count = self.h.list()
        total_length = 0
        for i in range(count):
            subarray = lltype.cast_opaque_ptr(PARRAY, array[i].object)
            assert subarray
            total_length += len(subarray)
        return total_length

    def get_items_w(self):
        array, count = self.h.list()
        result_list_w = []
        for i in range(count):
            subarray = lltype.cast_opaque_ptr(PARRAY, array[i].object)
            assert subarray
            for j in range(len(subarray)):
                w_item = unerase(subarray[j])
                result_list_w.append(w_item)
        return result_list_w

    def len_w(self, space):
        return space.wrap(self.get_length())

    def iter_w(self, space):
        return W_STMSetIter(self.h)


class W_STMSetIter(W_Root):
    _immutable_fields_ = ["hiter"]
    next_from_same_hash = 0

    def __init__(self, hobj):
        self.hiter = hobj.iterentries()

    def descr_iter(self, space):
        return self

    def descr_length_hint(self, space):
        # xxx estimate: doesn't remove the items already yielded,
        # and uses the faster len_estimate(); on the other hand,
        # counts only one for every 64-bit hash value
        return space.wrap(self.hiter.hashtable.len_estimate())

    def descr_next(self, space):
        if self.next_from_same_hash == 0:      # common case
            try:
                entry = self.hiter.next()
            except StopIteration:
                raise OperationError(space.w_StopIteration, space.w_None)
            index = 0
            array = lltype.cast_opaque_ptr(PARRAY, entry.object)
        else:
            index = self.next_from_same_hash
            array = self.next_array
            self.next_from_same_hash = 0
            self.next_array = lltype.nullptr(ARRAY)
        #
        if len(array) > index + 1:      # uncommon case
            self.next_from_same_hash = index + 1
            self.next_array = array
        #
        return unerase(array[index])

    def _cleanup_(self):
        raise Exception("seeing a prebuilt %r object" % (
            self.__class__,))


def W_STMSet___new__(space, w_subtype):
    r = space.allocate_instance(W_STMSet, w_subtype)
    r.__init__()
    return space.wrap(r)

W_STMSet.typedef = TypeDef(
    'pypystm.stmset',
    __new__ = interp2app(W_STMSet___new__),
    __contains__ = interp2app(W_STMSet.contains_w),
    add = interp2app(W_STMSet.add_w),
    remove = interp2app(W_STMSet.remove_w),
    discard = interp2app(W_STMSet.discard_w),

    __len__ = interp2app(W_STMSet.len_w),
    __iter__ = interp2app(W_STMSet.iter_w),
    )

W_STMSetIter.typedef = TypeDef(
    "stmset_iter",
    __iter__ = interp2app(W_STMSetIter.descr_iter),
    next = interp2app(W_STMSetIter.descr_next),
    __length_hint__ = interp2app(W_STMSetIter.descr_length_hint),
    )

"""
The class pypystm.stmset, giving a part of the regular 'set' interface
"""

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, WrappedDefault

from rpython.rlib import rstm, jit
from rpython.rlib.rgc import ll_arraycopy
from rpython.rlib.objectmodel import specialize
from rpython.rtyper.annlowlevel import cast_gcref_to_instance
from rpython.rtyper.annlowlevel import cast_instance_to_gcref
from rpython.rtyper.lltypesystem import lltype, llmemory

ARRAY = lltype.GcArray(llmemory.GCREF)
PARRAY = lltype.Ptr(ARRAY)


def find_equal_item(space, array, w_key):
    w_item = cast_gcref_to_instance(W_Root, array[0])
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
        w_item = cast_gcref_to_instance(W_Root, array[i])
        if space.eq_w(w_key, w_item):
            return i
        i += 1
        if i >= limit:
            return -1


class W_STMSet(W_Root):

    def __init__(self):
        self.h = rstm.create_hashtable()

    def contains_w(self, space, w_key):
        hkey = space.hash_w(w_key)
        gcref = self.h.get(hkey)
        array = lltype.cast_opaque_ptr(PARRAY, gcref)
        if array and find_equal_item(space, array, w_key) >= 0:
            return space.w_True
        return space.w_False

    def add_w(self, space, w_key):
        hkey = space.hash_w(w_key)
        gcref = self.h.get(hkey)
        array = lltype.cast_opaque_ptr(PARRAY, gcref)
        if array:
            if find_equal_item(space, array, w_key) >= 0:
                return      # already there
            L = len(array)
            narray = lltype.malloc(ARRAY, L + 1)
            ll_arraycopy(array, narray, 0, 0, L)
        else:
            narray = lltype.malloc(ARRAY, 1)
            L = 0
        narray[L] = cast_instance_to_gcref(w_key)
        gcref = lltype.cast_opaque_ptr(llmemory.GCREF, narray)
        self.h.set(hkey, gcref)

    def try_remove(self, space, w_key):
        hkey = space.hash_w(w_key)
        gcref = self.h.get(hkey)
        array = lltype.cast_opaque_ptr(PARRAY, gcref)
        if not array:
            return False
        i = find_equal_item(space, array, w_key)
        if i < 0:
            return False
        # found
        L = len(array) - 1
        if L == 0:
            narray = lltype.nullptr(ARRAY)
        else:
            narray = lltype.malloc(ARRAY, L)
            ll_arraycopy(array, narray, 0, 0, i)
            ll_arraycopy(array, narray, i + 1, i, L - i)
        gcref = lltype.cast_opaque_ptr(llmemory.GCREF, narray)
        self.h.set(hkey, gcref)
        return True

    def remove_w(self, space, w_key):
        if not self.try_remove(space, w_key):
            space.raise_key_error(w_key)

    def discard_w(self, space, w_key):
        self.try_remove(space, w_key)


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
    )

"""
The class pypystm.stmdict, giving a part of the regular 'dict' interface
"""

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault

from rpython.rlib import rstm, jit, rgc
from rpython.rlib.objectmodel import specialize, we_are_translated
from rpython.rtyper.annlowlevel import cast_gcref_to_instance
from rpython.rtyper.annlowlevel import cast_instance_to_gcref
from rpython.rtyper.lltypesystem import lltype, llmemory

ARRAY = lltype.GcArray(llmemory.GCREF)
PARRAY = lltype.Ptr(ARRAY)


def find_equal_item(space, array, w_key):
    w_item = cast_gcref_to_instance(W_Root, array[0])
    if space.eq_w(w_key, w_item):
        return 0
    if len(array) > 2:
        return _run_next_iterations(space, array, w_key)
    return -1

@jit.dont_look_inside
def _run_next_iterations(space, array, w_key):
    i = 2
    limit = len(array)
    while True:
        w_item = cast_gcref_to_instance(W_Root, array[i])
        if space.eq_w(w_key, w_item):
            return i
        i += 2
        if i >= limit:
            return -1

def ll_arraycopy(source, dest, source_start, dest_start, length):
    if we_are_translated():
        rgc.ll_arraycopy(source, dest, source_start, dest_start, length)
    else:
        for i in range(length):
            dest[dest_start + i] = source[source_start + i]


class W_STMDict(W_Root):

    def __init__(self):
        self.h = rstm.create_hashtable()

    def getitem_w(self, space, w_key):
        hkey = space.hash_w(w_key)
        gcref = self.h.get(hkey)
        array = lltype.cast_opaque_ptr(PARRAY, gcref)
        if array:
            i = find_equal_item(space, array, w_key)
            if i >= 0:
                return cast_gcref_to_instance(W_Root, array[i + 1])
        space.raise_key_error(w_key)

    def setitem_w(self, space, w_key, w_value):
        hkey = space.hash_w(w_key)
        entry = self.h.lookup(hkey)
        array = lltype.cast_opaque_ptr(PARRAY, entry.object)
        if array:
            i = find_equal_item(space, array, w_key)
            if i >= 0:
                # already there, update the value
                array[i + 1] = cast_instance_to_gcref(w_value)
                return
            L = len(array)
            narray = lltype.malloc(ARRAY, L + 2)
            ll_arraycopy(array, narray, 0, 0, L)
        else:
            narray = lltype.malloc(ARRAY, 2)
            L = 0
        narray[L] = cast_instance_to_gcref(w_key)
        narray[L + 1] = cast_instance_to_gcref(w_value)
        entry.object = lltype.cast_opaque_ptr(llmemory.GCREF, narray)

    def delitem_w(self, space, w_key):
        hkey = space.hash_w(w_key)
        entry = self.h.lookup(hkey)
        array = lltype.cast_opaque_ptr(PARRAY, entry.object)
        if array:
            i = find_equal_item(space, array, w_key)
            if i >= 0:
                # found
                L = len(array) - 2
                if L == 0:
                    narray = lltype.nullptr(ARRAY)
                else:
                    narray = lltype.malloc(ARRAY, L)
                    ll_arraycopy(array, narray, 0, 0, i)
                    ll_arraycopy(array, narray, i + 2, i, L - i)
                entry.object = lltype.cast_opaque_ptr(llmemory.GCREF, narray)
                return
        space.raise_key_error(w_key)

    def contains_w(self, space, w_key):
        hkey = space.hash_w(w_key)
        gcref = self.h.get(hkey)
        array = lltype.cast_opaque_ptr(PARRAY, gcref)
        if array and find_equal_item(space, array, w_key) >= 0:
            return space.w_True
        return space.w_False

    @unwrap_spec(w_default=WrappedDefault(None))
    def get_w(self, space, w_key, w_default):
        hkey = space.hash_w(w_key)
        gcref = self.h.get(hkey)
        array = lltype.cast_opaque_ptr(PARRAY, gcref)
        if array:
            i = find_equal_item(space, array, w_key)
            if i >= 0:
                return cast_gcref_to_instance(W_Root, array[i + 1])
        return w_default

    @unwrap_spec(w_default=WrappedDefault(None))
    def setdefault_w(self, space, w_key, w_default):
        hkey = space.hash_w(w_key)
        entry = self.h.lookup(hkey)
        array = lltype.cast_opaque_ptr(PARRAY, entry.object)
        if array:
            i = find_equal_item(space, array, w_key)
            if i >= 0:
                # already there, return the existing value
                return cast_gcref_to_instance(W_Root, array[i + 1])
            L = len(array)
            narray = lltype.malloc(ARRAY, L + 2)
            ll_arraycopy(array, narray, 0, 0, L)
        else:
            narray = lltype.malloc(ARRAY, 2)
            L = 0
        narray[L] = cast_instance_to_gcref(w_key)
        narray[L + 1] = cast_instance_to_gcref(w_default)
        entry.object = lltype.cast_opaque_ptr(llmemory.GCREF, narray)
        return w_default


def W_STMDict___new__(space, w_subtype):
    r = space.allocate_instance(W_STMDict, w_subtype)
    r.__init__()
    return space.wrap(r)

W_STMDict.typedef = TypeDef(
    'pypystm.stmset',
    __new__ = interp2app(W_STMDict___new__),
    __getitem__ = interp2app(W_STMDict.getitem_w),
    __setitem__ = interp2app(W_STMDict.setitem_w),
    __delitem__ = interp2app(W_STMDict.delitem_w),
    __contains__ = interp2app(W_STMDict.contains_w),
    get = interp2app(W_STMDict.get_w),
    setdefault = interp2app(W_STMDict.setdefault_w),
    )

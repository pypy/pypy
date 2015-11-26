"""
The class pypystm.hashtable, mapping integers to objects.
"""

from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault

from rpython.rlib import rstm, rerased
from rpython.rlib.rarithmetic import intmask

erase, unerase = rerased.new_erasing_pair("stmdictitem")


class W_Hashtable(W_Root):

    def __init__(self):
        self.h = rstm.create_hashtable()

    @unwrap_spec(key=int)
    def getitem_w(self, space, key):
        gcref = self.h.get(key)
        if not gcref:
            space.raise_key_error(space.wrap(key))
        return unerase(gcref)

    @unwrap_spec(key=int)
    def setitem_w(self, key, w_value):
        self.h.set(key, erase(w_value))

    @unwrap_spec(key=int)
    def delitem_w(self, space, key):
        entry = self.h.lookup(key)
        if not entry.object:
            space.raise_key_error(space.wrap(key))
        self.h.writeobj(entry, rstm.NULL_GCREF)

    @unwrap_spec(key=int)
    def contains_w(self, space, key):
        gcref = self.h.get(key)
        return space.newbool(not not gcref)

    @unwrap_spec(key=int, w_default=WrappedDefault(None))
    def get_w(self, space, key, w_default):
        gcref = self.h.get(key)
        if not gcref:
            return w_default
        return unerase(gcref)

    @unwrap_spec(key=int, w_default=WrappedDefault(None))
    def setdefault_w(self, space, key, w_default):
        entry = self.h.lookup(key)
        gcref = entry.object
        if not gcref:
            self.h.writeobj(entry, erase(w_default))
            return w_default
        return unerase(gcref)

    def len_w(self, space):
        return space.wrap(self.h.len())

    def keys_w(self, space):
        array, count = self.h.list()
        lst = [intmask(array[i].index) for i in range(count)]
        return space.newlist_int(lst)

    def values_w(self, space):
        array, count = self.h.list()
        lst_w = [unerase(array[i].object)
                 for i in range(count)]
        return space.newlist(lst_w)

    def items_w(self, space):
        array, count = self.h.list()
        lst_w = [space.newtuple([
            space.wrap(intmask(array[i].index)),
            unerase(array[i].object)])
                 for i in range(count)]
        return space.newlist(lst_w)

    def iterkeys_w(self, space):
        return W_HashtableIterKeys(self.h)

    def itervalues_w(self, space):
        return W_HashtableIterValues(self.h)

    def iteritems_w(self, space):
        return W_HashtableIterItems(self.h)


class W_BaseHashtableIter(W_Root):
    _immutable_fields_ = ["hiter"]

    def __init__(self, hobj):
        self.hiter = hobj.iterentries()

    def descr_iter(self, space):
        return self

    def descr_length_hint(self, space):
        # xxx overestimate: doesn't remove the items already yielded,
        # and uses the faster len_estimate()
        return space.wrap(self.hiter.hashtable.len_estimate())

    def descr_next(self, space):
        try:
            entry = self.hiter.next()
        except StopIteration:
            raise OperationError(space.w_StopIteration, space.w_None)
        return self.get_final_value(space, entry)

    def _cleanup_(self):
        raise Exception("seeing a prebuilt %r object" % (
            self.__class__,))

class W_HashtableIterKeys(W_BaseHashtableIter):
    def get_final_value(self, space, entry):
        return space.wrap(intmask(entry.index))

class W_HashtableIterValues(W_BaseHashtableIter):
    def get_final_value(self, space, entry):
        return unerase(entry.object)

class W_HashtableIterItems(W_BaseHashtableIter):
    def get_final_value(self, space, entry):
        return space.newtuple([
            space.wrap(intmask(entry.index)),
            unerase(entry.object)])


def W_Hashtable___new__(space, w_subtype):
    r = space.allocate_instance(W_Hashtable, w_subtype)
    r.__init__()
    return space.wrap(r)

W_Hashtable.typedef = TypeDef(
    'pypystm.hashtable',
    __new__ = interp2app(W_Hashtable___new__),
    __getitem__ = interp2app(W_Hashtable.getitem_w),
    __setitem__ = interp2app(W_Hashtable.setitem_w),
    __delitem__ = interp2app(W_Hashtable.delitem_w),
    __contains__ = interp2app(W_Hashtable.contains_w),
    get = interp2app(W_Hashtable.get_w),
    setdefault = interp2app(W_Hashtable.setdefault_w),

    __len__ = interp2app(W_Hashtable.len_w),
    keys    = interp2app(W_Hashtable.keys_w),
    values  = interp2app(W_Hashtable.values_w),
    items   = interp2app(W_Hashtable.items_w),

    __iter__   = interp2app(W_Hashtable.iterkeys_w),
    iterkeys   = interp2app(W_Hashtable.iterkeys_w),
    itervalues = interp2app(W_Hashtable.itervalues_w),
    iteritems  = interp2app(W_Hashtable.iteritems_w),
)

W_BaseHashtableIter.typedef = TypeDef(
    "hashtable_iter",
    __iter__ = interp2app(W_BaseHashtableIter.descr_iter),
    next = interp2app(W_BaseHashtableIter.descr_next),
    __length_hint__ = interp2app(W_BaseHashtableIter.descr_length_hint),
    )

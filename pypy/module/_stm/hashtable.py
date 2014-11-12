"""
The class _stm.hashtable, mapping integers to objects.
"""

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, unwrap_spec

from rpython.rlib import rstm
from rpython.rtyper.annlowlevel import cast_gcref_to_instance
from rpython.rtyper.annlowlevel import cast_instance_to_gcref


class W_Hashtable(W_Root):

    def __init__(self):
        self.h = rstm.create_hashtable()

    @unwrap_spec(key=int)
    def getitem_w(self, space, key):
        gcref = self.h.get(key)
        if not gcref:
            space.raise_key_error(space.wrap(key))
        return cast_gcref_to_instance(W_Root, gcref)

    @unwrap_spec(key=int)
    def setitem_w(self, key, w_value):
        gcref = cast_instance_to_gcref(w_value)
        self.h.set(key, gcref)

    @unwrap_spec(key=int)
    def delitem_w(self, key):
        self.h.set(key, rstm.NULL_GCREF)


def W_Hashtable___new__(space, w_subtype):
    r = space.allocate_instance(W_Hashtable, w_subtype)
    r.__init__()
    return space.wrap(r)

W_Hashtable.typedef = TypeDef(
    '_stm.hashtable',
    __new__ = interp2app(W_Hashtable___new__),
    __getitem__ = interp2app(W_Hashtable.getitem_w),
    __setitem__ = interp2app(W_Hashtable.setitem_w),
    __delitem__ = interp2app(W_Hashtable.delitem_w),
    )

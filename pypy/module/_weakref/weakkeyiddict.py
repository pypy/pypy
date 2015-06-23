#
# This is _weakref.weakkeyiddict(), a generally useful weak-keyed-dict
# with identity instead of equality. It is useful to add more
# attributes to existing objects, for example, without attaching
# them to the objects themselves.  It can be emulated in pure Python,
# of course, but given that we already have a class in rlib.rweakref
# that is doing exactly that in a cheap way, it is far more efficient
# this way.
#

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault

from rpython.rlib.rweakref import RWeakKeyDictionary


class W_WeakKeyIdDict(W_Root):
    def __init__(self):
        self.data = RWeakKeyDictionary(W_Root, W_Root)

    def getitem_w(self, space, w_key):
        w_value = self.data.get(w_key)
        if w_value is None:
            space.raise_key_error(w_key)
        return w_value

    def setitem_w(self, space, w_key, w_value):
        self.data.set(w_key, w_value)

    def delitem_w(self, space, w_key):
        if self.data.get(w_key) is None:
            space.raise_key_error(w_key)
        self.data.set(w_key, None)

    def contains_w(self, space, w_key):
        return space.wrap(self.data.get(w_key) is not None)

    @unwrap_spec(w_default=WrappedDefault(None))
    def get_w(self, space, w_key, w_default):
        w_value = self.data.get(w_key)
        if w_value is not None:
            return w_value
        else:
            return w_default

    def pop_w(self, space, w_key, w_default=None):
        w_value = self.data.get(w_key)
        if w_value is not None:
            self.data.set(w_key, None)
            return w_value
        elif w_default is not None:
            return w_default
        else:
            space.raise_key_error(w_key)

    @unwrap_spec(w_default=WrappedDefault(None))
    def setdefault_w(self, space, w_key, w_default):
        w_value = self.data.get(w_key)
        if w_value is not None:
            return w_value
        else:
            self.data.set(w_key, w_default)
            return w_default


def W_WeakKeyIdDict___new__(space, w_subtype):
    r = space.allocate_instance(W_WeakKeyIdDict, w_subtype)
    r.__init__()
    return space.wrap(r)

W_WeakKeyIdDict.typedef = TypeDef(
    '_weakref.weakkeyiddict',
    __new__ = interp2app(W_WeakKeyIdDict___new__),
    __getitem__ = interp2app(W_WeakKeyIdDict.getitem_w),
    __setitem__ = interp2app(W_WeakKeyIdDict.setitem_w),
    __delitem__ = interp2app(W_WeakKeyIdDict.delitem_w),
    __contains__ = interp2app(W_WeakKeyIdDict.contains_w),
    get = interp2app(W_WeakKeyIdDict.get_w),
    pop = interp2app(W_WeakKeyIdDict.pop_w),
    setdefault = interp2app(W_WeakKeyIdDict.setdefault_w),
)

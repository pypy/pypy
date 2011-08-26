from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.baseobjspace import Wrappable

class W_IdentityDict(Wrappable):
    def __init__(self, space):
        self.dict = {}

    def descr_new(space, w_subtype):
        self = space.allocate_instance(W_IdentityDict, w_subtype)
        W_IdentityDict.__init__(self, space)
        return space.wrap(self)

    def descr_len(self, space):
        return space.wrap(len(self.dict))

    def descr_contains(self, space, w_key):
        return space.wrap(w_key in self.dict)

    def descr_setitem(self, space, w_key, w_value):
        self.dict[w_key] = w_value

    def descr_getitem(self, space, w_key):
        try:
            return self.dict[w_key]
        except KeyError:
            raise OperationError(space.w_KeyError, w_key)

    def descr_delitem(self, space, w_key):
        try:
            del self.dict[w_key]
        except KeyError:
            raise OperationError(space.w_KeyError, w_key)

    def get(self, space, w_key, w_default=None):
        return self.dict.get(w_key, w_default)

    def keys(self, space):
        return space.newlist(self.dict.keys())

    def values(self, space):
        return space.newlist(self.dict.values())

    def clear(self, space):
        self.dict.clear()

W_IdentityDict.typedef = TypeDef("identity_dict",
    __doc__="""\
A dictionary that considers keys by object identity.
Distinct objects that compare equal will have separate entries.
All objects can be used as keys, even non-hashable ones.
""",
    __new__ = interp2app(W_IdentityDict.descr_new.im_func),
    __len__ = interp2app(W_IdentityDict.descr_len),
    __contains__ = interp2app(W_IdentityDict.descr_contains),
    __setitem__ = interp2app(W_IdentityDict.descr_setitem),
    __getitem__ = interp2app(W_IdentityDict.descr_getitem),
    __delitem__ = interp2app(W_IdentityDict.descr_delitem),
    get = interp2app(W_IdentityDict.get),
    keys = interp2app(W_IdentityDict.keys),
    values = interp2app(W_IdentityDict.values),
    clear = interp2app(W_IdentityDict.clear),
)

from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import ObjSpace, W_Root, NoneNotWrapped, interp2app
from pypy.interpreter.gateway import Arguments, unwrap_spec
from pypy.interpreter.baseobjspace import Wrappable

class W_IdentityDict(Wrappable):
    def __init__(self, space):
        self.dict = {}
    __init__.unwrap_spec = ['self', ObjSpace]

    @unwrap_spec(ObjSpace, W_Root)
    def descr_new(space, w_subtype):
        self = space.allocate_instance(W_IdentityDict, w_subtype)
        W_IdentityDict.__init__(self, space)
        return space.wrap(self)

    @unwrap_spec('self', ObjSpace)
    def descr_len(self, space):
        return space.wrap(len(self.dict))

    @unwrap_spec('self', ObjSpace, W_Root)
    def descr_contains(self, space, w_key):
        return space.wrap(w_key in self.dict)

    @unwrap_spec('self', ObjSpace, W_Root, W_Root)
    def descr_setitem(self, space, w_key, w_value):
        self.dict[w_key] = w_value

    @unwrap_spec('self', ObjSpace, W_Root)
    def descr_getitem(self, space, w_key):
        try:
            return self.dict[w_key]
        except KeyError:
            raise OperationError(space.w_KeyError, w_key)

    @unwrap_spec('self', ObjSpace, W_Root, W_Root)
    def get(self, space, w_key, w_default=None):
        return self.dict.get(w_key, w_default)

    @unwrap_spec('self', ObjSpace)
    def keys(self, space):
        return space.newlist(self.dict.keys())

    @unwrap_spec('self', ObjSpace)
    def values(self, space):
        return space.newlist(self.dict.values())

    @unwrap_spec('self', ObjSpace)
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
    get = interp2app(W_IdentityDict.get),
    keys = interp2app(W_IdentityDict.keys),
    values = interp2app(W_IdentityDict.values),
    clear = interp2app(W_IdentityDict.clear),
)

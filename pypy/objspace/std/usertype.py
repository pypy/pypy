from pypy.objspace.std.objspace import *
from typeobject import W_TypeObject


class W_UserType(W_TypeObject):

    # 'typename' is an instance property here

    def __init__(w_self, space, w_name, w_bases, w_dict):
        w_self.typename = space.unwrap(w_name)
        W_TypeObject.__init__(w_self, space)
        w_self.w_name   = w_name
        w_self.w_bases  = w_bases
        w_self.w_dict   = w_dict

    def getbases(w_self, space):
        return space.unpackiterable(w_self.w_bases)

    def lookup_exactly_here(w_self, space, w_key):
        try:
            w_value = space.getitem(w_self.w_dict, w_key)
        except OperationError, e:
            # catch KeyErrors and turn them into KeyErrors (real ones!)
            if not e.match(space, space.w_KeyError):
                raise
            raise KeyError
        return w_value


# XXX we'll worry about the __new__/__init__ distinction later
def usertype_new(space, w_usertype, w_args, w_kwds):
    # XXX no __init__ support at all here
    from userobject import W_UserObject
    return W_UserObject(space, w_usertype)

StdObjSpace.new.register(usertype_new, W_UserType, W_ANY, W_ANY)

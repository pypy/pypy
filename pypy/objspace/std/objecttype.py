from pypy.objspace.std.objspace import *
from typeobject import W_TypeObject


class W_ObjectType(W_TypeObject):
    """The single instance of W_ObjectType is what the user sees as
    '__builtin__.object'."""

    typename = 'object'
    staticbases = ()


# XXX we'll worry about the __new__/__init__ distinction later
def objecttype_new(space, w_objecttype, w_args, w_kwds):
    # XXX 2.2 behavior: ignoring all arguments
    from objectobject import W_ObjectObject
    return W_ObjectObject(space)

StdObjSpace.new.register(objecttype_new, W_ObjectType, W_ANY, W_ANY)

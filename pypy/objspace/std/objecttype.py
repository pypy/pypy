from pypy.objspace.std.objspace import *
from typeobject import W_TypeObject


class W_ObjectType(W_TypeObject):
    """The single instance of W_ObjectType is what the user sees as
    '__builtin__.object'."""

    typename = 'object'
    staticbases = ()

    # all multimethods that we want to be visible as object.__xxx__
    # should be defined here.

    object_getattr = StdObjSpace.getattr
    object_setattr = StdObjSpace.setattr
    object_delattr = StdObjSpace.delattr
    object_type    = StdObjSpace.type
    object_repr    = StdObjSpace.repr
    object_str     = StdObjSpace.str
    object_hash    = StdObjSpace.hash

    # this is a method in 'object' because it is not an object space operation
    object_init    = MultiMethod('__init__', 1, varargs=True, keywords=True)

registerimplementation(W_ObjectType)


def type_new__ObjectType_ObjectType(space, w_basetype, w_objecttype, w_args, w_kwds):
    # XXX 2.2 behavior: ignoring all arguments
    from objectobject import W_ObjectObject
    return W_ObjectObject(space), True


register_all(vars(), W_ObjectType)

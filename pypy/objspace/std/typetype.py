from pypy.objspace.std.objspace import *
from pypy.objspace.std.register_all import register_all
from typeobject import W_TypeObject, NewMultimethodCode

class W_TypeType(W_TypeObject):
    """The single instance of this class is the object the user sees as
    '__builtin__.type'."""

    typename = 'type'

registerimplementation(W_TypeType)


# XXX we'll worry about the __new__/__init__ distinction later
def new__TypeType_ANY_ANY(space, w_typetype, w_args, w_kwds):
    if space.is_true(w_kwds):
        raise OperationError(space.w_TypeError,
                             space.wrap("no keyword arguments expected"))
    args = space.unpackiterable(w_args)
    if len(args) == 1:
        return space.type(args[0])
    elif len(args) == 3:
        from usertype import W_UserType
        w_name, w_bases, w_dict = args
        w_usertype = W_UserType(space, w_name, w_bases, w_dict)
        return w_usertype
    else:
        raise OperationError(space.w_TypeError,
                             space.wrap("type() takes 1 or 3 arguments"))

register_all(vars())

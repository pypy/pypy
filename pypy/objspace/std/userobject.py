from pypy.objspace.std.objspace import *
from usertype import W_UserType
import typeobject


class W_UserObject(W_Object):
    delegate_once = {}

    def __init__(w_self, space, w_type):
        W_Object.__init__(w_self, space)
        w_self.w_type = w_type
        w_self.w_dict = space.newdict([])


def user_type(space, w_userobj):
    return w_userobj.w_type

StdObjSpace.type.register(user_type, W_UserObject)


def user_getattr(space, w_userobj, w_attr):
    try:
        w_value = space.getitem(w_userobj.w_dict, w_attr)
    except OperationError, e:
        # catch KeyErrors
        if not e.match(space, space.w_KeyError):
            raise
        raise FailedToImplement(space.w_AttributeError)
    return w_value

StdObjSpace.getattr.register(user_getattr, W_UserObject, W_ANY)


def user_setattr(space, w_userobj, w_attr, w_value):
    space.setitem(w_userobj.w_dict, w_attr, w_value)

StdObjSpace.setattr.register(user_setattr, W_UserObject, W_ANY, W_ANY)


def user_delattr(space, w_userobj, w_attr):
    space.delitem(w_userobj.w_dict, w_attr)

StdObjSpace.delattr.register(user_delattr, W_UserObject, W_ANY)

from pypy.objspace.std.objspace import *


class W_NoneObject(W_Object):
    delegate_once = {}
    statictypename = 'NoneType'


def none_unwrap(space, w_none):
    return None

StdObjSpace.unwrap.register(none_unwrap, W_NoneObject)

def none_is_true(space, w_none):
    return False

StdObjSpace.is_true.register(none_is_true, W_NoneObject)

from pypy.objspace.std.objspace import *


class W_NoneObject:
    delegate_once = {}


def none_unwrap(space, w_none):
    return None

StdObjSpace.unwrap.register(none_unwrap, W_NoneObject)

from pypy.objspace.std.stdtypedef import StdTypeDef
from pypy.interpreter import gateway


def descr__new__(space, w_type):
    return space.w_None

# ____________________________________________________________

none_typedef = StdTypeDef("NoneType",
    __new__ = gateway.interp2app(descr__new__)
    )
none_typedef.acceptable_as_base_class = False



from pypy.objspace.std.stdtypedef import *


# ____________________________________________________________

none_typedef = StdTypeDef("NoneType",
    )
none_typedef.acceptable_as_base_class = False

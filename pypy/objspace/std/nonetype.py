from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.objecttype import object_typedef


# ____________________________________________________________

none_typedef = StdTypeDef("NoneType", [object_typedef],
    )

"""
Reviewed 03-06-22
"""
from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.objecttype import object_typedef

# ____________________________________________________________

iter_typedef = StdTypeDef("sequence-iterator", [object_typedef],
    )

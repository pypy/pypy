from pypy.objspace.std.objspace import *


class W_ObjectObject(W_Object):
    """Instances of this class are what the user can directly see with an
    'object()' call."""
    from pypy.objspace.std.objecttype import object_typedef as typedef

# ____________________________________________________________


register_all(vars())

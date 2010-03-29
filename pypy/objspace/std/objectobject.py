from pypy.objspace.std.model import W_Object
from pypy.objspace.std.register_all import register_all


class W_ObjectObject(W_Object):
    """Instances of this class are what the user can directly see with an
    'object()' call."""
    from pypy.objspace.std.objecttype import object_typedef as typedef

# ____________________________________________________________


register_all(vars())

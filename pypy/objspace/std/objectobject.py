from pypy.objspace.std.objspace import *


class W_ObjectObject(W_Object):
    """Instances of this class are what the user can directly see with an
    'object()' call."""
    from pypy.objspace.std.objecttype import object_typedef as typedef


# any-to-object delegation is quite trivial, because W_ObjectObject is.
def delegate__ANY(space, w_obj):
    return W_ObjectObject(space)
delegate__ANY.result_class = W_ObjectObject
delegate__ANY.priority = PRIORITY_PARENT_TYPE

#def object_init__Object(space, w_object, w_args, w_kwds):
#    pass


register_all(vars())

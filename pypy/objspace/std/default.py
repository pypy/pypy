"""Default implementation for some operation."""

from pypy.objspace.std.register_all import register_all


# __init__ should succeed if called internally as a multimethod

def init__ANY(space, w_obj, __args__):
    pass

register_all(vars())

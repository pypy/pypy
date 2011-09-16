"""Default implementation for some operation."""

from pypy.interpreter.error import OperationError, typed_unwrap_error_msg
from pypy.objspace.std.register_all import register_all
from pypy.rlib import objectmodel


# The following default implementations are used before delegation is tried.
# 'id' is normally the address of the wrapper.

def id__ANY(space, w_obj):
    #print 'id:', w_obj
    return space.wrap(objectmodel.compute_unique_id(w_obj))

# __init__ should succeed if called internally as a multimethod

def init__ANY(space, w_obj, __args__):
    pass

def int_w__ANY(space,w_obj):
    raise OperationError(space.w_TypeError,
                         typed_unwrap_error_msg(space, "integer", w_obj))

def float_w__ANY(space,w_obj):
    raise OperationError(space.w_TypeError,
                         typed_unwrap_error_msg(space, "float", w_obj))

def uint_w__ANY(space,w_obj):
    raise OperationError(space.w_TypeError,
                         typed_unwrap_error_msg(space, "integer", w_obj))

def unicode_w__ANY(space,w_obj):
    raise OperationError(space.w_TypeError,
                         typed_unwrap_error_msg(space, "unicode", w_obj))

def bigint_w__ANY(space,w_obj):
    raise OperationError(space.w_TypeError,
                         typed_unwrap_error_msg(space, "integer", w_obj))

register_all(vars())

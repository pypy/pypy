"""Default implementation for some operation."""

from pypy.interpreter.error import OperationError
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

def typed_unwrap_error_msg(space, expected, w_obj):
    type_name = space.type(w_obj).getname(space, '?')
    return space.wrap("expected %s, got %s object" % (expected, type_name))

def int_w__ANY(space,w_obj):
    raise OperationError(space.w_TypeError,
                         typed_unwrap_error_msg(space, "integer", w_obj))

def str_w__ANY(space,w_obj):
    raise OperationError(space.w_TypeError,
                         typed_unwrap_error_msg(space, "string", w_obj))

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

def format__ANY_ANY(space, w_obj, w_format_spec):
    if space.isinstance_w(w_format_spec, space.w_unicode):
        w_as_str = space.unicode(w_obj)
    elif space.isinstance_w(w_format_spec, space.w_str):
        w_as_str = space.str(w_obj)
    else:
        msg = "format_spec must be a string"
        raise OperationError(space.w_TypeError, space.wrap(msg))
    return space.format(w_as_str)

register_all(vars())

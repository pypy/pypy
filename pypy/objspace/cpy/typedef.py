"""
Generic support to turn interpreter objects (subclasses of Wrappable)
into CPython objects (subclasses of W_Object) based on their typedef.
"""

from pypy.objspace.cpy.capi import *
from pypy.interpreter.baseobjspace import Wrappable, SpaceCache


class rpython_object(object):
    __slots__ = ('data',)
rpython_data = rpython_object.data
del rpython_object.data

def init_rpython_data(w_object, value):
    rpython_data.__set__(w_object.value, value)
    value.__cpy_wrapper__ = w_object

def get_rpython_data(w_object):
    return rpython_data.__get__(w_object.value)

def rpython2cpython(space, x):
    w_x = x.__cpy_wrapper__
    if w_x is None:
        w_type = space.fromcache(TypeDefCache).getorbuild(x.typedef)
        w_x = space.call_function(w_type)
        init_rpython_data(w_x, x)
    return w_x

def cpython2rpython(space, w_obj):
    if isinstance(w_obj.value, rpython_object):
        return get_rpython_data(w_obj)
    else:
        return None

# ____________________________________________________________

class TypeDefCache(SpaceCache):
    def build(cache, typedef):
        space = cache.space
        newtype = type(typedef.name, (rpython_object,), {})
        w_result = W_Object(newtype)
        space.wrap_cache[id(w_result)] = w_result, typedef, follow_annotations
        return w_result


def follow_annotations(bookkeeper, w_type):
    pass


# hack!
Wrappable.__cpy_wrapper__ = None

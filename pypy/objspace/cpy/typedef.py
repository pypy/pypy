"""
Generic support to turn interpreter objects (subclasses of Wrappable)
into CPython objects (subclasses of W_Object) based on their typedef.
"""

from pypy.objspace.cpy.capi import *
from pypy.interpreter.baseobjspace import Wrappable, SpaceCache

class TypeDefCache(SpaceCache):
    def build(cache, typedef):
        space = cache.space
        newtype = type(typedef.name, (), {})
        w_result = W_Object(newtype)
        space.wrap_cache[id(w_result)] = w_result, typedef, follow_annotations
        return w_result


def follow_annotations(bookkeeper, w_type):
    pass


# hack!
Wrappable.__cpy_wrapper__ = None

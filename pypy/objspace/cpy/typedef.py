"""
Generic support to turn interpreter objects (subclasses of Wrappable)
into CPython objects (subclasses of W_Object) based on their typedef.
"""

from pypy.objspace.cpy.capi import *
from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import Wrappable, SpaceCache
from pypy.rpython.objectmodel import we_are_translated
from pypy.rpython.rcpy import CPyTypeInterface, cpy_export, cpy_import
from pypy.rpython.rcpy import cpy_typeobject


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
    cache = space.fromcache(TypeDefCache)
    typeintf = cache.getorbuild(x.typedef)
    if we_are_translated():
        obj = cpy_export(typeintf, x)
        return W_Object(obj)
    else:
        w_x = x.__cpy_wrapper__
        if w_x is None:
            w_type = cache.wraptypeintf(x.typedef, typeintf)
            w_x = space.call_function(w_type)
            init_rpython_data(w_x, x)
        return w_x
rpython2cpython.allow_someobjects = True

def cpython2rpython_raw(space, w_obj):
    "NOT_RPYTHON."
    try:
        w_obj, result, follow = space.wrap_cache[id(w_obj)]
    except KeyError:
        if isinstance(w_obj.value, rpython_object):
            result = get_rpython_data(w_obj)
        else:
            result = None
    return result

def cpython2rpython(space, RequiredClass, w_obj):
    if we_are_translated():
        cache = space.fromcache(TypeDefCache)
        typeintf = cache.getorbuild(RequiredClass.typedef)
        cpytype = cpy_typeobject(typeintf, RequiredClass)
        w_cpytype = W_Object(cpytype)
        if space.is_true(space.isinstance(w_obj, w_cpytype)):
            x = w_obj.value
            return cpy_import(RequiredClass, x)
    else:
        result = cpython2rpython_raw(space, w_obj)
        if isinstance(result, RequiredClass):
            return result
    w_objtype = space.type(w_obj)
    w_name = space.getattr(w_objtype, space.wrap('__name__'))
    typename = space.str_w(w_name)
    msg = "'%s' object expected, got '%s' instead" % (
        RequiredClass.typedef.name, typename)
    raise OperationError(space.w_TypeError, space.wrap(msg))
cpython2rpython._annspecialcase_ = 'specialize:arg(1)'
cpython2rpython.allow_someobjects = True

# ____________________________________________________________

class TypeDefCache(SpaceCache):
    def __init__(self, space):
        super(TypeDefCache, self).__init__(space)
        self.wrappedtypes = {}

    def build(cache, typedef):
        typeintf = CPyTypeInterface(typedef.name)
        return typeintf

    def wraptypeintf(self, typedef, typeintf):
        # only when running on top of CPython, not for translation
        try:
            return self.wrappedtypes[typeintf]
        except KeyError:
            space = self.space
            newtype = typeintf.emulate(rpython_object)
            w_result = W_Object(newtype)
            space.wrap_cache[id(w_result)] = w_result, typedef, follow_annotations
            self.wrappedtypes[typeintf] = w_result
            return w_result

def follow_annotations(bookkeeper, w_type):
    pass


# hack!
Wrappable.__cpy_wrapper__ = None

"""
Generic support to turn interpreter objects (subclasses of Wrappable)
into CPython objects (subclasses of W_Object) based on their typedef.
"""

from pypy.objspace.cpy.capi import *
from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import Wrappable, SpaceCache
from pypy.interpreter.function import Function
from pypy.interpreter.typedef import GetSetProperty
from pypy.rpython.objectmodel import we_are_translated
from pypy.rpython.rcpy import CPyTypeInterface, cpy_export, cpy_import
from pypy.rpython.rcpy import cpy_typeobject, rpython_object
from pypy.rpython.rcpy import init_rpython_data, get_rpython_data
from pypy.rpython.lltypesystem import lltype


def rpython2cpython(space, x):
    cache = space.fromcache(TypeDefCache)
    typeintf = cache.getorbuild(x.typedef)
    if we_are_translated():
        obj = cpy_export(typeintf, x)
        return W_Object(obj)
    else:
        w_x = x.__cpy_wrapper__
        if w_x is None:
            w_type = cache.wraptypeintf(x.__class__, typeintf)
            w_x = W_Object(rpython_object.__new__(w_type.value))
            init_rpython_data(w_x.value, x)
            x.__cpy_wrapper__ = w_x
        return w_x
rpython2cpython.allow_someobjects = True
rpython2cpython._annspecialcase_ = "specialize:argtype(1)"

def rpython2cpytype(space, Cls):
    cache = space.fromcache(TypeDefCache)
    typeintf = cache.getorbuild(Cls.typedef)
    if we_are_translated():
        cpytype = cpy_typeobject(typeintf, Cls)
        return W_Object(cpytype)        
    else:
        return cache.wraptypeintf(Cls, typeintf)
rpython2cpytype.allow_someobjects = True
rpython2cpytype._annspecialcase_ = "specialize:arg(1)"
    
def cpython2rpython_raw(space, w_obj):
    "NOT_RPYTHON."
    try:
        w_obj, result, follow = space.wrap_cache[id(w_obj)]
    except KeyError:
        if isinstance(w_obj.value, rpython_object):
            result = get_rpython_data(w_obj.value)
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
        if typedef in (Function.typedef, GetSetProperty.typedef):
            raise ValueError("cannot wrap at run-time an interpreter object "
                             "of type %r" % (typedef.name,))
        space = cache.space
        objects = {}
        for name, value in typedef.rawdict.items():
            #if name.startswith('__') and name.endswith('__'):
            #    raise NotImplementedError("missing support for special "
            #                              "attributes in TypeDef-to-CPython "
            #                              "converter (%s.%s)" % (
            #        typedef.name, name))
            w_value = space.wrap(value)
            objects[name] = lltype.pyobjectptr(w_value.value)
        typeintf = CPyTypeInterface(typedef.name, objects)
        return typeintf

    def wraptypeintf(cache, cls, typeintf):
        "NOT_RPYTHON.  Not available after translation."
        try:
            return cache.wrappedtypes[cls]
        except KeyError:
            typedef = cls.typedef
            space = cache.space
            newtype = typeintf.emulate(cls)
            w_result = W_Object(newtype)
            space.wrap_cache[id(w_result)] = w_result, typedef, follow_annotations
            cache.wrappedtypes[cls] = w_result
            return w_result

def follow_annotations(bookkeeper, w_type):
    pass


# hack!
Wrappable.__cpy_wrapper__ = None

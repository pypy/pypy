from pypy.interpreter.error import OperationError
from pypy.objspace.descroperation import Object
from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.objspace import StdObjSpace


def descr__repr__(space, w_obj):
    w = space.wrap
    classname = space.unwrap(space.getattr(space.type(w_obj), w("__name__")))
    id = space.unwrap(space.id(w_obj))
    return w("<%s object at 0x%x>" % (classname, id))

def descr__str__(space, w_obj):
    return space.repr(w_obj)

def descr__hash__(space, w_obj):
    # XXX detect non-hashable instances (the ones overriding comparison only)
    return space.id(w_obj)

def descr__class__(space, w_obj):
    return space.type(w_obj)

def descr__new__(space, w_type, __args__):
    from pypy.objspace.std.objectobject import W_ObjectObject
    # don't allow arguments if the default object.__init__() is about
    # to be called
    w_parentinit, w_ignored = w_type.lookup_where('__init__')
    if w_parentinit is space.w_object and (__args__.args_w or __args__.kwds_w):
        raise OperationError(space.w_TypeError,
                             space.wrap("default __new__ takes no parameters"))
    w_obj = space.allocate_instance(W_ObjectObject, w_type)
    w_obj.__init__(space)
    return w_obj

def descr__init__(space, w_obj, __args__):
    pass

# ____________________________________________________________

object_typedef = StdTypeDef("object",
    __getattribute__ = gateway.interp2app(Object.descr__getattribute__.im_func),
    __setattr__ = gateway.interp2app(Object.descr__setattr__.im_func),
    __delattr__ = gateway.interp2app(Object.descr__delattr__.im_func),
    __str__ = gateway.interp2app(descr__str__),
    __repr__ = gateway.interp2app(descr__repr__),
    __hash__ = gateway.interp2app(descr__hash__),
    __class__ = GetSetProperty(descr__class__),
    __new__ = newmethod(descr__new__),
    __init__ = gateway.interp2app(descr__init__),
    )

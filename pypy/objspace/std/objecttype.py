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

def descr__new__(space, w_type, *args_w, **kwds_w):
    # XXX 2.2 behavior: ignoring all arguments
    from objectobject import W_ObjectObject
    w_obj = W_ObjectObject(space)
    return space.w_object.check_user_subclass(w_type, w_obj)

# ____________________________________________________________

object_typedef = StdTypeDef("object", [],
    __getattribute__ = gateway.interp2app(Object.descr__getattribute__.im_func),
    __setattr__ = gateway.interp2app(Object.descr__setattr__.im_func),
    __delattr__ = gateway.interp2app(Object.descr__delattr__.im_func),
    __str__ = gateway.interp2app(descr__str__),
    __repr__ = gateway.interp2app(descr__repr__),
    __hash__ = gateway.interp2app(descr__hash__),
    __class__ = GetSetProperty(descr__class__),
    __new__ = newmethod(descr__new__),
    )

from pypy.objspace.std.stdtypedef import *
from pypy.interpreter.typedef import default_dict_descr


def descr__new__(space, w_typetype, w_name, w_bases, w_dict):
    "This is used to create user-defined classes only."
    from pypy.objspace.std.typeobject import W_TypeObject
    # XXX check types
    name = space.unwrap(w_name)
    assert isinstance(name, str)
    bases_w = space.unpackiterable(w_bases)
    dict_w = {}
    dictkeys_w = space.unpackiterable(w_dict)
    for w_key in dictkeys_w:
        key = space.unwrap(w_key)
        assert isinstance(key, str)
        dict_w[key] = space.getitem(w_dict, w_key)
    w_type = space.allocate_instance(W_TypeObject, w_typetype)
    w_type.__init__(space, name, bases_w or [space.w_object], dict_w)
    return w_type

def descr_get__mro__(space, w_type):
    # XXX this should be inside typeobject.py
    return space.newtuple(w_type.mro_w)

def descr__bases(space, w_type):
    return space.newtuple(w_type.bases_w)

# ____________________________________________________________

type_typedef = StdTypeDef("type",
    __new__ = newmethod(descr__new__),
    __name__ = attrproperty('name'),
    __bases__ = GetSetProperty(descr__bases),
    __mro__ = GetSetProperty(descr_get__mro__),
    __dict__ = default_dict_descr,
    )

from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.objecttype import object_typedef


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
    # XXX classmethod-ify w_dict['__new__']
    w_type = W_TypeObject(space, name, bases_w or [space.w_object], dict_w, None)
    return space.w_type.check_user_subclass(w_typetype, w_type)

def descr_get__mro__(space, w_type):
    # XXX this should be inside typeobject.py
    return space.newtuple(w_type.getmro())

def descr__dict__(space, w_type):
    # XXX should return a <dictproxy object>
    dictspec = []
    for key, w_value in w_type.dict_w.items():
        dictspec.append((space.wrap(key), w_value))
    return space.newdict(dictspec)

def descr__bases(space, w_type):
    return space.newtuple(w_type.bases_w)

# ____________________________________________________________

type_typedef = StdTypeDef("type", [object_typedef],
    __new__ = newmethod(descr__new__),
    __name__ = attrproperty('name'),
    __bases__ = GetSetProperty(descr__bases),
    __dict__ = GetSetProperty(descr__dict__),
    __mro__ = GetSetProperty(descr_get__mro__),
    )
